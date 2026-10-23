"""行情数据访问：数据源调度、磁盘缓存与增量刷新。"""

from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timedelta

import numpy as np

from . import cache
from .models import Bars, DataError, Stock
from .sources import BaostockSource, MarketDataSource

ADJUST_LABELS = {"qfq": "前复权", "hfq": "后复权", "none": "不复权"}
FREQ_LABELS = {"d": "日K", "w": "周K", "m": "月K"}

RECENT_DAYS = 365 * 3
CACHE_TTL = timedelta(hours=6)
OVERLAP_DAYS = 10
BACKFILL_DAYS = 365 * 2

_source: MarketDataSource = BaostockSource()


def set_source(source: MarketDataSource) -> None:
    """切换行情数据源，应在创建窗口前调用；缓存按数据源名称隔离。"""
    global _source
    _source = source


def source_name() -> str:
    return _source.name


def search_stocks(keyword: str) -> list[Stock]:
    """按名称模糊搜索标的。"""
    return _source.search(keyword)


def _recent_start(freq: str) -> str:
    if freq != "d":
        return _source.full_start(freq)
    start = date.today() - timedelta(days=RECENT_DAYS)
    return max(_source.full_start(freq), start.isoformat())


def _refresh(old: Bars, requested_start: str, want_full: bool) -> Bars:
    if want_full and not old.full:
        fresh = _source.fetch(
            old.code, old.freq, old.adjust, old.is_index, requested_start
        )
        return replace(fresh, full=True)
    overlap_start = str(old.dates[-1] - np.timedelta64(OVERLAP_DAYS, "D"))
    start = max(overlap_start, requested_start)
    fresh = _source.fetch(old.code, old.freq, old.adjust, old.is_index, start)

    if not cache.overlaps_unchanged(old, fresh):
        # 复权因子变了（除权除息），增量数据与旧缓存接不上，只能整段重取
        refetch_start = (
            _source.full_start(old.freq) if old.full else requested_start
        )
        fresh = _source.fetch(
            old.code, old.freq, old.adjust, old.is_index, refetch_start
        )
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
    if freq not in FREQ_LABELS:
        raise ValueError(f"未知周期：{freq}")
    if adjust not in ADJUST_LABELS:
        raise ValueError(f"未知复权方式：{adjust}")
    want_full = full or freq != "d"
    requested_start = _source.full_start(freq) if want_full else _recent_start(freq)
    cached = cache.load(_source.name, code, freq, adjust)
    if cached is not None:
        bars, fetched_at = cached
        if (not want_full or bars.full) and datetime.now() - fetched_at < CACHE_TTL:
            return bars
    try:
        if cached is None:
            bars = _source.fetch(code, freq, adjust, is_index, requested_start)
            bars = replace(bars, full=want_full)
        else:
            bars = _refresh(cached[0], requested_start, want_full)
    except DataError:
        if cached is not None:
            return cached[0]
        raise
    cache.save(_source.name, bars, datetime.now())
    return bars


def fetch_older(current: Bars) -> Bars:
    """向更早方向补一段历史，合并后写回缓存。"""
    if current.full:
        return current
    full_start = np.datetime64(_source.full_start(current.freq), "D")
    earliest = current.dates[0]
    if earliest <= full_start:
        return replace(current, full=True)
    start = max(full_start, earliest - np.timedelta64(BACKFILL_DAYS, "D"))
    cached = cache.load(_source.name, current.code, current.freq, current.adjust)
    fetched_at = cached[1] if cached is not None else datetime.now()
    older = _source.fetch(
        current.code,
        current.freq,
        current.adjust,
        current.is_index,
        str(start),
        str(earliest),
    )
    merged = cache.merge(older, current)
    if len(merged) <= len(current):
        complete = replace(current, full=True)
        cache.save(_source.name, complete, fetched_at)
        return complete
    merged = replace(merged, full=bool(start <= full_start))
    cache.save(_source.name, merged, fetched_at)
    return merged
