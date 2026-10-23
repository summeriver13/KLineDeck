"""K 线磁盘缓存：按数据源/标的/周期/复权存 npz，支持增量合并。"""

from __future__ import annotations

import json
import os
import shutil
import zipfile
from datetime import datetime
from pathlib import Path

import numpy as np

from .models import Bars

CACHE_VERSION = 2
ARRAY_FIELDS = (
    "dates",
    "open",
    "high",
    "low",
    "close",
    "preclose",
    "volume",
    "amount",
    "turn",
    "pct_chg",
)
PRICE_TOLERANCE = 1e-4


def _cache_roots() -> tuple[Path, Path]:
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return base / "KLineDeck" / "cache", base / "CandleLine" / "cache"
    base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    return base / "klinedeck", base / "candleline"


def cache_dir() -> Path:
    override = os.environ.get("KLINEDECK_CACHE_DIR")
    if override:
        return Path(override)
    path, legacy = _cache_roots()
    if not path.exists() and legacy.is_dir():
        try:
            shutil.copytree(legacy, path, dirs_exist_ok=True)
        except OSError:
            pass
    return path


def _safe(name: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in name)


def cache_path(source: str, code: str, freq: str, adjust: str) -> Path:
    return cache_dir() / _safe(source) / f"{code}_{freq}_{adjust}.npz"


def save(source: str, bars: Bars, fetched_at: datetime) -> None:
    path = cache_path(source, bars.code, bars.freq, bars.adjust)
    meta = {
        "version": CACHE_VERSION,
        "source": source,
        "code": bars.code,
        "freq": bars.freq,
        "adjust": bars.adjust,
        "is_index": bars.is_index,
        "full": bars.full,
        "fetched_at": fetched_at.isoformat(timespec="seconds"),
    }
    payload = {name: getattr(bars, name) for name in ARRAY_FIELDS}
    payload["dates"] = bars.dates.astype("int64")
    payload["meta"] = np.array(json.dumps(meta, ensure_ascii=False))
    tmp = path.with_name(f"{path.stem}.tmp.npz")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(tmp, **payload)
        os.replace(tmp, path)
    except OSError:
        tmp.unlink(missing_ok=True)


def load(
    source: str, code: str, freq: str, adjust: str
) -> tuple[Bars, datetime] | None:
    path = cache_path(source, code, freq, adjust)
    try:
        with np.load(path, allow_pickle=False) as bundle:
            meta = json.loads(str(bundle["meta"]))
            arrays = {name: np.array(bundle[name]) for name in ARRAY_FIELDS}
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile):
        return None
    if meta.get("version") != CACHE_VERSION:
        return None
    if (meta.get("source"), meta.get("code"), meta.get("freq"), meta.get("adjust")) != (
        source,
        code,
        freq,
        adjust,
    ):
        return None
    if any(len(value) != len(arrays["dates"]) for value in arrays.values()):
        return None
    dates = arrays["dates"].astype("datetime64[D]")
    if len(dates) == 0 or np.any(np.diff(dates.astype("int64")) <= 0):
        return None
    try:
        fetched_at = datetime.fromisoformat(meta["fetched_at"])
    except (KeyError, TypeError, ValueError):
        return None
    bars = Bars(
        code=code,
        freq=freq,
        adjust=adjust,
        is_index=bool(meta.get("is_index", False)),
        dates=dates,
        **{name: arrays[name] for name in ARRAY_FIELDS if name != "dates"},
        full=bool(meta.get("full", False)),
    )
    return bars, fetched_at


def overlaps_unchanged(old: Bars, new: Bars) -> bool:
    common = np.intersect1d(old.dates, new.dates, assume_unique=True)
    if len(common) == 0:
        return True
    old_rows = np.searchsorted(old.dates, common)
    new_rows = np.searchsorted(new.dates, common)
    for name in ("open", "close"):
        if not np.allclose(
            getattr(old, name)[old_rows],
            getattr(new, name)[new_rows],
            rtol=PRICE_TOLERANCE,
            atol=1e-6,
            equal_nan=True,
        ):
            return False
    return True


def merge(old: Bars, new: Bars) -> Bars:
    prefix = old.dates < new.dates[0]
    values = {
        name: np.concatenate((getattr(old, name)[prefix], getattr(new, name)))
        for name in ARRAY_FIELDS
    }
    return Bars(
        code=old.code,
        freq=old.freq,
        adjust=old.adjust,
        is_index=old.is_index,
        **values,
        full=old.full or new.full,
    )
