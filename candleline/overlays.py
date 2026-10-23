"""主图与成交量叠加：BOLL 与成交量均线。"""

from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from .data import Bars
from .indicators import boll, sma
from .theme import BOLL_COLORS, FAINT, MA_COLORS, TEXT


class BollOverlay:
    def __init__(self, plot: pg.PlotItem) -> None:
        self._plot = plot
        self._visible = False
        self._values: dict[str, np.ndarray] = {}
        self._items: list[pg.PlotDataItem] = []

    def set_bars(self, bars: Bars) -> None:
        mid, upper, lower = boll(bars.close)
        self._values = {"MID": mid, "UPPER": upper, "LOWER": lower}
        self._rebuild()

    def set_visible(self, visible: bool) -> None:
        self._visible = visible
        self._rebuild()

    def values(self, index: int) -> list[tuple[str, str, str]]:
        if not self._visible or not self._values:
            return []
        result: list[tuple[str, str, str]] = []
        labels = {"UPPER": "BOLL上", "MID": "BOLL中", "LOWER": "BOLL下"}
        for name, color in BOLL_COLORS.items():
            value = self._values[name][index]
            text = "—" if not np.isfinite(value) else f"{value:.2f}"
            result.append((labels[name], color, text))
        return result

    def _rebuild(self) -> None:
        for item in self._items:
            self._plot.removeItem(item)
        self._items.clear()
        if not self._visible or not self._values:
            return
        x = np.arange(len(self._values["MID"]))
        for name, color in BOLL_COLORS.items():
            item = pg.PlotDataItem(
                x,
                self._values[name],
                pen=pg.mkPen(color, width=1.0),
                connect="finite",
            )
            item.setZValue(-5)
            self._plot.addItem(item)
            self._items.append(item)


class LastPriceLine:
    def __init__(self, plot: pg.PlotItem) -> None:
        pen = pg.mkPen(FAINT, width=1, style=Qt.PenStyle.DotLine)
        self._item = pg.InfiniteLine(
            pos=0,
            angle=0,
            pen=pen,
            label="",
            labelOpts={
                "position": 0.985,
                "color": TEXT,
                "fill": pg.mkBrush(QColor(20, 26, 36, 220)),
            },
        )
        plot.addItem(self._item, ignoreBounds=True)
        self._item.setVisible(False)

    def set_price(self, price: float) -> None:
        self._item.setPos(price)
        self._item.label.setText(f"{price:.2f}")
        self._item.setVisible(True)


class VolumeMAOverlay:
    def __init__(self, plot: pg.PlotItem) -> None:
        self._plot = plot
        self._items: list[pg.PlotDataItem] = []

    def set_bars(self, bars: Bars, factor: float) -> None:
        for item in self._items:
            self._plot.removeItem(item)
        self._items.clear()
        x = np.arange(len(bars))
        for period, color in ((5, MA_COLORS[5]), (10, MA_COLORS[10])):
            item = pg.PlotDataItem(
                x,
                sma(bars.volume, period) / factor,
                pen=pg.mkPen(color, width=1.0),
                connect="finite",
            )
            self._plot.addItem(item)
            self._items.append(item)
