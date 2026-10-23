"""数据层：Baostock 行情查询、K 线缓存与绘图。"""

from __future__ import annotations

import threading
from contextlib import contextmanager
from datetime import date
from typing import Any, Iterator

import baostock as bs
import mplfinance as mpf
import pandas as pd

KLINE_FIELDS = "date,code,open,high,low,close,volume,turn,pctChg"
START_DATE = {"d": "2020-01-01", "w": "2020-01-01", "m": "2010-01-01"}
FREQ_NAMES = {"d": "日K", "w": "周K", "m": "月K"}
DEFAULT_BARS = 100
SHARES_PER_WAN_HAND = 1_000_000  # baostock 的 volume 单位是股，1 万手 = 100 万股
BACKGROUND = "#d1d4d9"  # 原 (0.82, 0.83, 0.85)，新版 mplfinance 只接受颜色字符串

_session_lock = threading.Lock()


class DataError(RuntimeError):
    """行情查询失败。"""


@contextmanager
def _session() -> Iterator[None]:
    # baostock 的登录状态是进程级全局变量，并发调用会互相顶掉，这里串行化
    with _session_lock:
        login = bs.login()
        if login.error_code != "0":
            raise DataError(f"登录 Baostock 失败：{login.error_msg}")
        try:
            yield
        finally:
            bs.logout()


def _fetch_rows(result: Any) -> list[list[str]]:
    if result.error_code != "0":
        raise DataError(result.error_msg)
    rows: list[list[str]] = []
    while result.next():
        rows.append(result.get_row_data())
    return rows


def search_stocks(keyword: str) -> list[tuple[str, str]]:
    """按名称模糊搜索在市 A 股，返回 [(代码, 名称)]。"""
    keyword = keyword.strip()
    if not keyword:
        return []
    with _session():
        result = bs.query_stock_basic(code_name=keyword)
        rows = _fetch_rows(result)
    records = [dict(zip(result.fields, row)) for row in rows]
    return [
        (record["code"], record["code_name"])
        for record in records
        if record["type"] == "1" and record["status"] == "1"
    ]


def fetch_kline(code: str, freq: str) -> pd.DataFrame:
    """取一只股票的某个周期 K 线：日期作索引，其余列为数值。"""
    if freq not in START_DATE:
        raise ValueError(f"未知周期：{freq}")
    with _session():
        result = bs.query_history_k_data_plus(
            code,
            KLINE_FIELDS,
            start_date=START_DATE[freq],
            end_date=date.today().isoformat(),
            frequency=freq,
            adjustflag="3",
        )
        rows = _fetch_rows(result)
    if not rows:
        raise DataError(f"{code} 自 {START_DATE[freq]} 起没有 {FREQ_NAMES[freq]} 数据")
    frame = pd.DataFrame(rows, columns=result.fields)
    frame["date"] = pd.to_datetime(frame["date"])
    frame = frame.drop(columns=["code"]).set_index("date")
    return frame.apply(pd.to_numeric, errors="coerce")


# 视觉参数：中国股市习惯，红涨绿跌
my_color = mpf.make_marketcolors(
    up="r", down="g", edge="inherit", wick="inherit", volume="inherit"
)
my_style = mpf.make_mpf_style(
    marketcolors=my_color, figcolor=BACKGROUND, gridcolor=BACKGROUND
)

title_font = {
    "fontname": "SimHei",
    "size": "16",
    "color": "black",
    "va": "bottom",
    "ha": "center",
}
normal_label_font = {
    "fontname": "SimHei",
    "size": "12",
    "color": "black",
    "va": "bottom",
    "ha": "left",
}
large_red_font = {
    "fontname": "Arial",
    "size": "16",
    "color": "red",
    "weight": "bold",
    "va": "bottom",
    "ha": "left",
}
large_green_font = {
    "fontname": "Arial",
    "size": "16",
    "color": "green",
    "weight": "bold",
    "va": "bottom",
    "ha": "left",
}
small_red_font = {
    "fontname": "Arial",
    "size": "12",
    "color": "red",
    "weight": "bold",
    "va": "bottom",
    "ha": "left",
}
small_green_font = {
    "fontname": "Arial",
    "size": "12",
    "color": "green",
    "weight": "bold",
    "va": "bottom",
    "ha": "left",
}
normal_font = {
    "fontname": "Arial",
    "size": "12",
    "color": "black",
    "va": "bottom",
    "ha": "left",
}


class Candle:
    """一只股票的 K 线数据，按周期惰性加载并缓存。"""

    def __init__(self, code: str, name: str) -> None:
        self.code = code
        self.name = name
        self._frames: dict[str, pd.DataFrame] = {}

    def update(self, code: str, name: str) -> None:
        self.code = code
        self.name = name
        self._frames.clear()

    def frame(self, freq: str) -> pd.DataFrame:
        if freq not in self._frames:
            self._frames[freq] = fetch_kline(self.code, freq)
        return self._frames[freq]

    def make_figure(self, data: pd.DataFrame, freq: str) -> mpf.Mpf_Figure:
        plot_data = data.iloc[-DEFAULT_BARS:]
        last = plot_data.iloc[-1]
        rising = last["close"] >= last["open"]
        figure = mpf.figure(style=my_style, figsize=(12, 8), facecolor=BACKGROUND)
        ax1 = figure.add_axes([0.06, 0.25, 0.88, 0.60])
        ax2 = figure.add_axes([0.06, 0.15, 0.88, 0.10], sharex=ax1)
        ax1.set_ylabel("price")
        ax2.set_ylabel("volume")
        figure.text(
            0.50,
            0.95,
            f"{self.code} - {self.name}（{FREQ_NAMES[freq]}）",
            **title_font,
        )
        self._quote_text(figure, last, rising)
        mpf.plot(plot_data, ax=ax1, volume=ax2, type="candle", style=my_style)
        return figure

    @staticmethod
    def _quote_text(figure: Any, last: pd.Series, rising: bool) -> None:
        price_font = large_red_font if rising else large_green_font
        detail_font = small_red_font if rising else small_green_font
        change_font = normal_font
        if last["pctChg"] > 0:
            change_font = small_red_font
        elif last["pctChg"] < 0:
            change_font = small_green_font
        items = [
            (0.06, 0.11, 0.90, "开: ", f"{last['open']:.2f}", price_font),
            (0.06, 0.11, 0.86, "收: ", f"{last['close']:.2f}", price_font),
            (0.20, 0.25, 0.90, "高: ", f"{last['high']:.2f}", detail_font),
            (0.20, 0.25, 0.86, "低: ", f"{last['low']:.2f}", detail_font),
            (0.34, 0.40, 0.90, "换手: ", f"{last['turn']:.2f}%", normal_font),
            (0.34, 0.40, 0.86, "涨跌: ", f"{last['pctChg']:.2f}%", change_font),
            (
                0.52,
                0.64,
                0.90,
                "量(万手): ",
                f"{last['volume'] / SHARES_PER_WAN_HAND:.2f}",
                normal_font,
            ),
        ]
        for label_x, value_x, y, label, value, value_font in items:
            figure.text(label_x, y, label, **normal_label_font)
            figure.text(value_x, y, value, **value_font)
