"""价格、成交量与副图共享的十字光标。"""

from __future__ import annotations

import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from .theme import TEXT

CROSSHAIR = "#5b6b82"


class Crosshair:
    def __init__(
        self,
        price: pg.PlotItem,
        volume: pg.PlotItem,
        indicator: pg.PlotItem,
    ) -> None:
        pen = pg.mkPen(CROSSHAIR, width=1, style=Qt.PenStyle.DashLine)
        self._verticals: list[pg.InfiniteLine] = []
        for plot in (price, volume, indicator):
            line = pg.InfiniteLine(angle=90, movable=False, pen=pen)
            plot.addItem(line, ignoreBounds=True)
            line.setVisible(False)
            self._verticals.append(line)
        self._hline = pg.InfiniteLine(angle=0, movable=False, pen=pen)
        price.addItem(self._hline, ignoreBounds=True)
        self._hline.setVisible(False)
        self._hline.label = pg.InfLineLabel(
            self._hline,
            text="",
            position=0.985,
            color=TEXT,
            fill=pg.mkBrush(QColor(20, 26, 36, 230)),
        )

    def show(self, index: float, price_y: float | None = None) -> None:
        for line in self._verticals:
            line.setPos(index)
            line.setVisible(True)
        if price_y is None:
            self._hline.setVisible(False)
            return
        self._hline.setPos(price_y)
        self._hline.setVisible(True)
        self._hline.label.setText(f"{price_y:.2f}")

    def hide(self) -> None:
        for line in self._verticals:
            line.setVisible(False)
        self._hline.setVisible(False)
