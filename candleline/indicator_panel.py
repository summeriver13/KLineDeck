"""副图指标：MACD / KDJ / RSI 的绘制与十字光标读数。"""

from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt

from .data import Bars
from .indicators import kdj, macd, rsi
from .theme import BORDER, DOWN, GRID, MA_COLORS, MUTED, UP

KINDS = {"macd": "MACD(12,26,9)", "kdj": "KDJ(9,3,3)", "rsi": "RSI(6,12,24)"}
GUIDES = {"macd": (0.0,), "kdj": (20.0, 80.0), "rsi": (30.0, 70.0)}


class IndicatorPanel:
    def __init__(self) -> None:
        self.plot = pg.PlotItem()
        self.plot.setMenuEnabled(False)
        self.plot.hideButtons()
        self.plot.showGrid(x=True, y=True, alpha=0.07)
        self.plot.getViewBox().setMouseEnabled(x=True, y=False)
        self.plot.getViewBox().setDefaultPadding(0.02)
        self.plot.showAxis("right")
        self.plot.hideAxis("left")
        axis = self.plot.getAxis("right")
        axis.setWidth(64)
        axis.enableAutoSIPrefix(False)
        axis.setStyle(tickTextOffset=6)
        axis.setTextPen(pg.mkPen(MUTED))
        axis.setPen(pg.mkPen(BORDER))
        self._kind = "macd"
        self._bars: Bars | None = None
        self._values: dict[str, np.ndarray] = {}
        self._items: list[object] = []
        self._guides: list[pg.InfiniteLine] = []
        self._title = pg.TextItem("", color=MUTED, anchor=(0, 0))
        self.plot.addItem(self._title, ignoreBounds=True)
        self._title.hide()

    @property
    def kind(self) -> str:
        return self._kind

    def set_bars(self, bars: Bars) -> None:
        self._bars = bars
        dif, dea, hist = macd(bars.close)
        k, d, j = kdj(bars.high, bars.low, bars.close)
        self._values = {
            "dif": dif,
            "dea": dea,
            "hist": hist,
            "k": k,
            "d": d,
            "j": j,
            "rsi6": rsi(bars.close, 6),
            "rsi12": rsi(bars.close, 12),
            "rsi24": rsi(bars.close, 24),
        }
        self._draw()

    def set_kind(self, kind: str) -> None:
        if kind not in KINDS:
            raise ValueError(f"未知副图指标：{kind}")
        self._kind = kind
        self._draw()

    def sync_y_range(self, first: int, last: int) -> None:
        if self._bars is None or last < first:
            return
        if self._kind == "macd":
            arrays = [self._values[name][first : last + 1] for name in ("dif", "dea", "hist")]
            low = min(0.0, float(np.nanmin(np.concatenate(arrays))))
            high = max(0.0, float(np.nanmax(np.concatenate(arrays))))
        elif self._kind == "kdj":
            arrays = [self._values[name][first : last + 1] for name in ("k", "d", "j")]
            low = min(0.0, float(np.nanmin(np.concatenate(arrays))))
            high = max(100.0, float(np.nanmax(np.concatenate(arrays))))
        else:
            arrays = [self._values[name][first : last + 1] for name in ("rsi6", "rsi12", "rsi24")]
            low, high = 0.0, 100.0
            finite = np.concatenate(arrays)
            finite = finite[np.isfinite(finite)]
            if finite.size:
                low = min(0.0, float(finite.min()))
                high = max(100.0, float(finite.max()))
        if not np.isfinite(low) or not np.isfinite(high) or high <= low:
            return
        padding = (high - low) * 0.08
        self.plot.getViewBox().setYRange(low - padding, high + padding, padding=0)
        x_low, x_high = self.plot.getViewBox().viewRange()[0]
        self._title.setPos(
            x_low + (x_high - x_low) * 0.008,
            high + padding * 0.2,
        )

    def values(self, index: int) -> list[tuple[str, str, str]]:
        if self._bars is None or index < 0 or index >= len(self._bars):
            return []
        if self._kind == "macd":
            return [
                _cell("DIF", MA_COLORS[5], self._values["dif"][index]),
                _cell("DEA", MA_COLORS[10], self._values["dea"][index]),
                _cell(
                    "MACD",
                    UP if self._values["hist"][index] >= 0 else DOWN,
                    self._values["hist"][index],
                ),
            ]
        if self._kind == "kdj":
            return [
                _cell("K", MA_COLORS[5], self._values["k"][index]),
                _cell("D", MA_COLORS[10], self._values["d"][index]),
                _cell("J", MA_COLORS[20], self._values["j"][index]),
            ]
        return [
            _cell("RSI6", MA_COLORS[5], self._values["rsi6"][index]),
            _cell("RSI12", MA_COLORS[10], self._values["rsi12"][index]),
            _cell("RSI24", MA_COLORS[20], self._values["rsi24"][index]),
        ]

    def _draw(self) -> None:
        self._clear()
        if self._bars is None:
            self._title.hide()
            return
        self._title.setText(KINDS[self._kind])
        self._title.show()
        x = np.arange(len(self._bars))
        for level in GUIDES[self._kind]:
            guide = pg.InfiniteLine(
                pos=level,
                angle=0,
                movable=False,
                pen=pg.mkPen(GRID, width=1, style=Qt.PenStyle.DashLine),
            )
            self.plot.addItem(guide, ignoreBounds=True)
            self._guides.append(guide)
        if self._kind == "macd":
            hist = self._values["hist"]
            brushes = [pg.mkBrush(UP if value >= 0 else DOWN) for value in hist]
            self._add(
                pg.BarGraphItem(x=x, height=hist, width=0.72, brushes=brushes, pen=None)
            )
            self._add(
                pg.PlotDataItem(
                    x,
                    self._values["dif"],
                    pen=pg.mkPen(MA_COLORS[5], width=1.0),
                    connect="finite",
                )
            )
            self._add(
                pg.PlotDataItem(
                    x,
                    self._values["dea"],
                    pen=pg.mkPen(MA_COLORS[10], width=1.0),
                    connect="finite",
                )
            )
        elif self._kind == "kdj":
            for name, color in (("k", MA_COLORS[5]), ("d", MA_COLORS[10]), ("j", MA_COLORS[20])):
                self._add(
                    pg.PlotDataItem(
                        x,
                        self._values[name],
                        pen=pg.mkPen(color, width=1.0),
                        connect="finite",
                    )
                )
        else:
            for name, color in (
                ("rsi6", MA_COLORS[5]),
                ("rsi12", MA_COLORS[10]),
                ("rsi24", MA_COLORS[20]),
            ):
                self._add(
                    pg.PlotDataItem(
                        x,
                        self._values[name],
                        pen=pg.mkPen(color, width=1.0),
                        connect="finite",
                    )
                )

    def _add(self, item: object) -> None:
        self.plot.addItem(item)
        self._items.append(item)

    def _clear(self) -> None:
        for item in self._items:
            self.plot.removeItem(item)
        self._items.clear()
        for guide in self._guides:
            self.plot.removeItem(guide)
        self._guides.clear()


def _cell(label: str, color: str, value: float) -> tuple[str, str, str]:
    text = "—" if not np.isfinite(value) else f"{value:.2f}"
    return label, color, text
