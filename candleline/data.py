"""Baostock 数据访问：股票搜索与复权 K 线。"""

from __future__ import annotations

import re
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date
from typing import Any, Iterator

import baostock as bs
import numpy as np

FIELDS_DAILY = "date,open,high,low,close,preclose,volume,amount,turn,pctChg"
FIELDS_PERIOD = "date,open,high,low,close,volume,amount,turn,pctChg"
ADJUST_FLAGS = {"qfq": "2", "hfq": "1", "none": "3"}  # 前复权 / 后复权 / 不复权
ADJUST_LABELS = {"qfq": "前复权", "hfq": "后复权", "none": "不复权"}
START_DATES = {"d": "2010-01-01", "w": "2005-01-01", "m": "2000-01-01"}
FREQ_LABELS = {"d": "日K", "w": "周K", "m": "月K"}
STOCK_PREFIXES = ("sh.60", "sh.68", "sz.00", "sz.30")
INDEX_PREFIXES = ("sh.000", "sz.399")
A_SHARE = re.compile(r"^(sh\.(60|68)|sz\.(00|30))")

_session_lock = threading.Lock()


class DataError(RuntimeError):
    """行情查询失败。"""


@dataclass(frozen=True)
class Stock:
    code: str
    name: str
    is_index: bool = False


@dataclass(frozen=True)
class Bars:
    code: str
    freq: str
    adjust: str
    is_index: bool
    dates: np.ndarray
    open: np.ndarray
    high: np.ndarray
    low: np.ndarray
    close: np.ndarray
    preclose: np.ndarray
    volume: np.ndarray
    amount: np.ndarray
    turn: np.ndarray
    pct_chg: np.ndarray

    def __len__(self) -> int:
        return len(self.dates)


@contextmanager
def _session() -> Iterator[None]:
    # baostock 的登录态是进程级全局变量，串行化避免并发互踢
    with _session_lock:
        login = bs.login()
        if login.error_code != "0":
            raise DataError(f"登录 Baostock 失败：{login.error_msg}")
        try:
            yield
        finally:
            bs.logout()


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


def search_stocks(keyword: str) -> list[Stock]:
    """按名称模糊搜索 A 股与指数，返回按代码排序的结果。"""
    keyword = keyword.strip()
    if not keyword:
        return []
    with _session():
        result = bs.query_stock_basic(code_name=keyword)
        rows = _rows(result)
    stocks: list[Stock] = []
    for row in rows:
        record = dict(zip(result.fields, row))
        if record.get("status") != "1":
            continue
        code = record["code"]
        if record.get("type") == "1" and code.startswith(STOCK_PREFIXES):
            stocks.append(Stock(code, record["code_name"], False))
        elif record.get("type") == "2" and code.startswith(INDEX_PREFIXES):
            stocks.append(Stock(code, record["code_name"], True))
    return sorted(stocks, key=lambda stock: stock.code)


def fetch_bars(code: str, freq: str, adjust: str, is_index: bool = False) -> Bars:
    """取一只标的的复权 K 线，按日期升序。"""
    if freq not in START_DATES:
        raise ValueError(f"未知周期：{freq}")
    if adjust not in ADJUST_FLAGS:
        raise ValueError(f"未知复权方式：{adjust}")
    fields_text = FIELDS_DAILY if freq == "d" else FIELDS_PERIOD
    with _session():
        result = bs.query_history_k_data_plus(
            code,
            fields_text,
            start_date=START_DATES[freq],
            end_date=date.today().isoformat(),
            frequency=freq,
            adjustflag=ADJUST_FLAGS[adjust],
        )
        rows = _rows(result)
        fields = list(result.fields)
    if not rows:
        raise DataError(f"{code} 没有可用的 {freq} 数据")
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
