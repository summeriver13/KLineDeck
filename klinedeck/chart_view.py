"""图表区间、视口映射与向左补历史的触发条件。"""

from __future__ import annotations

import numpy as np
import pyqtgraph as pg

from .data import Bars

RANGE_DAYS = {"1m": 30, "3m": 90, "6m": 180, "1y": 365, "3y": 1095, "all": None}
RANGE_LABELS = {"1m": "1月", "3m": "3月", "6m": "6月", "1y": "1年", "3y": "3年", "all": "全部"}
HISTORY_TRIGGER_BARS = 90


class HistoryGate:
    """限制同一批数据只触发一次补历史，并在重建图表时复位。"""

    def __init__(self) -> None:
        self._requested = False
        self._suspended = False

    def begin(self) -> None:
        self._requested = False
        self._suspended = True

    def end(self) -> None:
        self._suspended = False

    def allow(self) -> None:
        self._requested = False

    def should_request(self, bars: Bars | None, first: int) -> bool:
        if self._suspended or bars is None or bars.full:
            return False
        if first > HISTORY_TRIGGER_BARS or self._requested:
            return False
        self._requested = True
        return True


def range_start(bars: Bars, key: str) -> int:
    days = RANGE_DAYS.get(key)
    if days is None:
        return 0
    cutoff = bars.dates[-1] - np.timedelta64(days, "D")
    return int(np.searchsorted(bars.dates, cutoff))


def visible_dates(bars: Bars, view: pg.ViewBox) -> tuple[np.datetime64, np.datetime64] | None:
    if len(bars) == 0:
        return None
    left, right = view.viewRange()[0]
    first = max(0, int(np.floor(left)))
    last = min(len(bars) - 1, int(np.ceil(right)) - 1)
    if last < first:
        return None
    return bars.dates[first], bars.dates[last]


def set_view_dates(
    bars: Bars,
    view: pg.ViewBox,
    first_date: np.datetime64,
    last_date: np.datetime64,
) -> None:
    if len(bars) == 0:
        return
    start = int(np.searchsorted(bars.dates, first_date))
    end = int(np.searchsorted(bars.dates, last_date, side="right"))
    start = min(start, len(bars) - 1)
    end = max(start + 1, min(end, len(bars)))
    view.setXRange(start, end, padding=0)


def configure_plot(plot: pg.PlotItem) -> None:
    plot.setMenuEnabled(False)
    plot.hideButtons()
    plot.showGrid(x=True, y=True, alpha=0.07)
    plot.getViewBox().setMouseEnabled(x=True, y=False)
    plot.getViewBox().setDefaultPadding(0.02)
