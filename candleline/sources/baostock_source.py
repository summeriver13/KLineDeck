"""Baostock 数据源：会话复用、股票搜索与复权 K 线解析。"""

from __future__ import annotations

import atexit
import threading
from contextlib import suppress
from datetime import date
from typing import Any, Callable, TypeVar

import baostock as bs
import numpy as np

from ..models import Bars, DataError, Stock

FIELDS_DAILY = "date,open,high,low,close,preclose,volume,amount,turn,pctChg"
FIELDS_PERIOD = "date,open,high,low,close,volume,amount,turn,pctChg"
ADJUST_FLAGS = {"qfq": "2", "hfq": "1", "none": "3"}  # 前复权 / 后复权 / 不复权
FULL_START = {"d": "2010-01-01", "w": "2005-01-01", "m": "2000-01-01"}
STOCK_PREFIXES = ("sh.60", "sh.68", "sz.00", "sz.30")
INDEX_PREFIXES = ("sh.000", "sz.399")

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


class BaostockSource:
    name = "baostock"

    def full_start(self, freq: str) -> str:
        return FULL_START[freq]

    def search(self, keyword: str) -> list[Stock]:
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

    def fetch(
        self,
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
