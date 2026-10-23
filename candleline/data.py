"""Baostock 数据访问：股票搜索、复权 K 线、磁盘缓存与增量刷新。"""

from __future__ import annotations

import atexit
import threading
from contextlib import suppress
from dataclasses import replace
from datetime import date, datetime, timedelta
from typing import Any, Callable, TypeVar

import baostock as bs
import numpy as np

from . import cache
from .models import Bars, DataError, Stock

FIELDS_DAILY = "date,open,high,low,close,preclose,volume,amount,turn,pctChg"
FIELDS_PERIOD = "date,open,high,low,close,volume,amount,turn,pctChg"
ADJUST_FLAGS = {"qfq": "2", "hfq": "1", "none": "3"}  # 前复权 / 后复权 / 不复权
ADJUST_LABELS = {"qfq": "前复权", "hfq": "后复权", "none": "不复权"}
FULL_START = {"d": "2010-01-01", "w": "2005-01-01", "m": "2000-01-01"}
FREQ_LABELS = {"d": "日K", "w": "周K", "m": "月K"}
STOCK_PREFIXES = ("sh.60", "sh.68", "sz.00", "sz.30")
INDEX_PREFIXES = ("sh.000", "sz.399")

RECENT_DAYS = 365 * 3
CACHE_TTL = timedelta(hours=6)
OVERLAP_DAYS = 10

_session_lock = threading.Lock()
_logged_in = False
T = TypeVar("T")


def _login() -> None:
    global _logged_in
    if _logged_in:
        return
    result = bs.login()
    if result.error_code != "0":
        raise DataError(f"登录 Baostock 失败：{result.error_msg}")
    _logged_in = True


def _logout() -> None:
    global _logged_in
    if not _logged_in:
        return
    _logged_in = False
    with suppress(Exception):
        bs.logout()


atexit.register(_logout)


def _call(action: Callable[[], T]) -> T:
    """串行化进程级的 Baostock 会话，掉线时重登一次。"""
    with _session_lock:
        for attempt in range(2):
            _login()
            try:
                return action()
            except DataError:
                _logout()
                if attempt == 1:
                    raise
    raise AssertionError("unreachable")


def _rows(result: Any) -> list[list[str]]:
    if result.error_code != "0":
        raise DataError(result.error_msg)
    rows: list[list[str]] = []
    while result.next():
        rows.append(result.get_row_data())
    return rows


def _column(rows: list[list[str]], index: int) -> np.ndarray:
    return np.array(
        [float(row[index]) if row[index] not in ("", None) else np.nan for row in rows],
        dtype=float,
    )


def _recent_start() -> str:
    start = date.today() - timedelta(days=RECENT_DAYS)
    return max(FULL_START["d"], start.isoformat())


def search_stocks(keyword: str) -> list[Stock]:
    """按名称模糊搜索 A 股与指数，返回按代码排序的结果。"""
    keyword = keyword.strip()
    if not keyword:
        return []

    def action() -> tuple[list[str], list[list[str]]]:
        result = bs.query_stock_basic(code_name=keyword)
        return list(result.fields), _rows(result)

    fields, rows = _call(action)
    stocks: list[Stock] = []
    for row in rows:
        record = dict(zip(fields, row))
        if record.get("status") != "1":
            continue
        code = record["code"]
        if record.get("type") == "1" and code.startswith(STOCK_PREFIXES):
            stocks.append(Stock(code, record["code_name"], False))
        elif record.get("type") == "2" and code.startswith(INDEX_PREFIXES):
            stocks.append(Stock(code, record["code_name"], True))
    return sorted(stocks, key=lambda stock: stock.code)


def _parse(
    code: str,
    freq: str,
    adjust: str,
    is_index: bool,
    fields: list[str],
    rows: list[list[str]],
) -> Bars:
    index = {name: position for position, name in enumerate(fields)}
    dates = np.array([row[index["date"]] for row in rows], dtype="datetime64[D]")
    close = _column(rows, index["close"])
    if "preclose" in index:
        preclose = _column(rows, index["preclose"])
    else:
        preclose = np.concatenate(([np.nan], close[:-1]))
    valid = ~np.isnan(close)
    if not valid.any():
        raise DataError(f"{code} 的 K 线全部无效")
    return Bars(
        code=code,
        freq=freq,
        adjust=adjust,
        is_index=is_index,
        dates=dates[valid],
        open=_column(rows, index["open"])[valid],
        high=_column(rows, index["high"])[valid],
        low=_column(rows, index["low"])[valid],
        close=close[valid],
        preclose=preclose[valid],
        volume=_column(rows, index["volume"])[valid],
        amount=_column(rows, index["amount"])[valid],
        turn=_column(rows, index["turn"])[valid],
        pct_chg=_column(rows, index["pctChg"])[valid],
    )


def _query_bars(
    code: str,
    freq: str,
    adjust: str,
    is_index: bool,
    start: str,
) -> Bars:
    fields_text = FIELDS_DAILY if freq == "d" else FIELDS_PERIOD

    def action() -> tuple[list[str], list[list[str]]]:
        result = bs.query_history_k_data_plus(
            code,
            fields_text,
            start_date=start,
            end_date=date.today().isoformat(),
            frequency=freq,
            adjustflag=ADJUST_FLAGS[adjust],
        )
        return list(result.fields), _rows(result)

    fields, rows = _call(action)
    if not rows:
        raise DataError(f"{code} 没有可用的 {freq} 数据")
    return _parse(code, freq, adjust, is_index, fields, rows)


def _refresh(
    old: Bars,
    requested_start: str,
    want_full: bool,
) -> Bars:
    if want_full and not old.full:
        fresh = _query_bars(old.code, old.freq, old.adjust, old.is_index, requested_start)
        return replace(fresh, full=True)
    overlap_start = str(old.dates[-1] - np.timedelta64(OVERLAP_DAYS, "D"))
    start = max(overlap_start, requested_start)
    fresh = _query_bars(old.code, old.freq, old.adjust, old.is_index, start)

    if not cache.overlaps_unchanged(old, fresh):
        # 复权因子变了（除权除息），增量数据与旧缓存接不上，只能整段重取
        refetch_start = FULL_START[old.freq] if old.full else requested_start
        fresh = _query_bars(old.code, old.freq, old.adjust, old.is_index, refetch_start)
        return replace(fresh, full=old.full or want_full)
    if len(fresh) == 0:
        return old
    merged = cache.merge(old, fresh)
    return replace(merged, full=old.full or want_full)


def fetch_bars(
    code: str,
    freq: str,
    adjust: str,
    is_index: bool = False,
    full: bool = False,
) -> Bars:
    """取复权 K 线：优先缓存，过期则增量刷新；full 表示取全部历史。"""
    if freq not in FULL_START:
        raise ValueError(f"未知周期：{freq}")
    if adjust not in ADJUST_FLAGS:
        raise ValueError(f"未知复权方式：{adjust}")
    want_full = full or freq != "d"
    requested_start = FULL_START[freq] if want_full else _recent_start()
    cached = cache.load(code, freq, adjust)
    if cached is not None:
        bars, fetched_at = cached
        if (not want_full or bars.full) and datetime.now() - fetched_at < CACHE_TTL:
            return bars
    try:
        if cached is None:
            bars = _query_bars(code, freq, adjust, is_index, requested_start)
            bars = replace(bars, full=want_full)
        else:
            bars = _refresh(cached[0], requested_start, want_full)
    except DataError:
        if cached is not None:
            return cached[0]
        raise
    cache.save(bars, datetime.now())
    return bars
