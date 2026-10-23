"""K 线图控件：蜡烛、成交量、副图指标、十字光标与区间缩放。"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import QEvent, Signal
from PySide6.QtWidgets import QVBoxLayout, QWidget

from .chart_view import (
    HistoryGate,
    configure_plot,
    range_start,
    set_view_dates,
    visible_dates,
)
from .crosshair import Crosshair
from .data import Bars
from .indicator_panel import IndicatorPanel
from .info import InfoBar
from .items import CandleItem, DateAxis, moving_average
from .overlays import BollOverlay, LastPriceLine, VolumeMAOverlay
from .theme import BG, BORDER, DOWN, MA_COLORS, MUTED, UP

MA_PERIODS = tuple(MA_COLORS)
DENSE_BARS = 900


class ChartWidget(QWidget):
    history_needed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._bars: Bars | None = None
        self._candle: CandleItem | None = None
        self._close_line: pg.PlotDataItem | None = None
        self._volume_bars: pg.BarGraphItem | None = None
        self._ma_items: dict[int, pg.PlotDataItem] = {}
        self._ma_values: dict[int, np.ndarray] = {}
        self._hover_index: int | None = None
        self._ma_visible = True
        self._range_key = "1y"
        self._history = HistoryGate()
        self._volume_factor = 1e6
        self._volume_unit = "万手"

        self.info = InfoBar()
        self.glw = pg.GraphicsLayoutWidget()
        self.glw.setBackground(BG)
        self.price = self.glw.addPlot(row=0, col=0)
        self.volume = self.glw.addPlot(row=1, col=0)
        self.indicator = IndicatorPanel()
        self.glw.addItem(self.indicator.plot, row=2, col=0)
        self.glw.ci.layout.setRowStretchFactor(0, 5)
        self.glw.ci.layout.setRowStretchFactor(1, 1)
        self.glw.ci.layout.setRowStretchFactor(2, 2)

        configure_plot(self.price)
        configure_plot(self.volume)
        self.price.hideAxis("left")
        self.price.showAxis("right")
        self.volume.hideAxis("left")
        self.volume.showAxis("right")
        self.price.hideAxis("bottom")
        self.volume.hideAxis("bottom")
        self.volume.setXLink(self.price)
        self.indicator.plot.setXLink(self.price)
        for plot in (self.price, self.volume, self.indicator.plot):
            axis = plot.getAxis("right")
            axis.setWidth(64)
            axis.enableAutoSIPrefix(False)
            axis.setStyle(tickTextOffset=6)
            axis.setTextPen(pg.mkPen(MUTED))
            axis.setPen(pg.mkPen(BORDER))

        self.volume_date = DateAxis()
        self.volume.setAxisItems({"bottom": self.volume_date})
        self.indicator_date = DateAxis()
        self.indicator.plot.setAxisItems({"bottom": self.indicator_date})
        for axis in (self.volume_date, self.indicator_date):
            axis.setStyle(tickTextOffset=6)
            axis.setTextPen(pg.mkPen(MUTED))
            axis.setPen(pg.mkPen(BORDER))

        self.price.getViewBox().sigXRangeChanged.connect(self._sync_y_range)
        self.boll = BollOverlay(self.price)
        self.volume_ma = VolumeMAOverlay(self.volume)
        self.last_line = LastPriceLine(self.price)
        self.crosshair = Crosshair(self.price, self.volume, self.indicator.plot)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 10)
        layout.setSpacing(6)
        layout.addWidget(self.info)
        layout.addWidget(self.glw, 1)

        self.glw.scene().sigMouseMoved.connect(self._on_mouse)
        self.glw.viewport().installEventFilter(self)

    @property
    def bars(self) -> Bars | None:
        return self._bars

    def set_bars(self, bars: Bars, preserve_view: bool = False) -> None:
        view_dates = (
            visible_dates(self._bars, self.price.getViewBox())
            if preserve_view and self._bars is not None
            else None
        )
        self._bars = bars
        self._history.begin()
        self._clear_items()
        x = np.arange(len(bars))
        self._candle = CandleItem(bars.open, bars.high, bars.low, bars.close, UP, DOWN)
        self._candle.setZValue(-10)
        self.price.addItem(self._candle)

        self._close_line = pg.PlotDataItem(
            x,
            bars.close,
            pen=pg.mkPen("#9aa6b8", width=1.1),
        )
        self._close_line.setVisible(False)
        self.price.addItem(self._close_line)

        self._volume_factor = 1e8 if bars.is_index else 1e6
        self._volume_unit = "亿手" if bars.is_index else "万手"
        brushes = [
            pg.mkBrush(UP if close >= open_ else DOWN)
            for open_, close in zip(bars.open, bars.close)
        ]
        self._volume_bars = pg.BarGraphItem(
            x=x,
            height=bars.volume / self._volume_factor,
            width=0.72,
            brushes=brushes,
            pen=None,
        )
        self.volume.addItem(self._volume_bars)
        self.volume.setLabel("right", self._volume_unit)

        for period in MA_PERIODS:
            values = moving_average(bars.close, period)
            self._ma_values[period] = values
            item = pg.PlotDataItem(
                x,
                values,
                pen=pg.mkPen(MA_COLORS[period], width=1.1),
                connect="finite",
            )
            item.setVisible(self._ma_visible)
            self.price.addItem(item)
            self._ma_items[period] = item

        self.boll.set_bars(bars)
        self.volume_ma.set_bars(bars, self._volume_factor)
        self.indicator.set_bars(bars)
        self.last_line.set_price(bars.close[-1])
        self.volume_date.set_dates(bars.dates)
        self.indicator_date.set_dates(bars.dates)
        self.price.getViewBox().setLimits(xMin=-1, xMax=max(1, len(bars)))
        if view_dates is None:
            self.set_range(self._range_key)
        else:
            set_view_dates(self._bars, self.price.getViewBox(), *view_dates)
        self._history.end()
        self._sync_y_range(None, self.price.getViewBox().viewRange()[0])
        self._update_info(len(bars) - 1)

    def _clear_items(self) -> None:
        if self._candle is not None:
            self.price.removeItem(self._candle)
            self._candle = None
        if self._close_line is not None:
            self.price.removeItem(self._close_line)
            self._close_line = None
        if self._volume_bars is not None:
            self.volume.removeItem(self._volume_bars)
            self._volume_bars = None
        for item in self._ma_items.values():
            self.price.removeItem(item)
        self._ma_items.clear()
        self._ma_values.clear()

    def set_range(self, key: str) -> None:
        self._range_key = key
        if self._bars is None or len(self._bars) == 0:
            return
        view = self.price.getViewBox()
        start = range_start(self._bars, key)
        view.setXRange(max(0, start - 1), len(self._bars), padding=0)

    def _sync_y_range(self, view: object, x_range: Sequence[float]) -> None:
        """把 y 轴锁到当前可见区间，并决定蜡烛或收盘线展示。"""
        if self._bars is None or len(self._bars) == 0:
            return
        left, right = x_range
        first = max(0, int(np.floor(left)))
        last = min(len(self._bars) - 1, int(np.ceil(right)))
        if last < first:
            return
        low = float(np.nanmin(self._bars.low[first : last + 1]))
        high = float(np.nanmax(self._bars.high[first : last + 1]))
        if not np.isfinite(low) or not np.isfinite(high) or high <= low:
            return
        padding = (high - low) * 0.06
        self.price.getViewBox().setYRange(low - padding, high + padding, padding=0)
        volume = float(np.nanmax(self._bars.volume[first : last + 1]))
        volume /= self._volume_factor
        self.volume.getViewBox().setYRange(0, max(volume * 1.25, 1e-9), padding=0)
        self.indicator.sync_y_range(first, last)
        dense = last - first + 1 > DENSE_BARS
        if self._candle is not None:
            self._candle.setVisible(not dense)
        if self._close_line is not None:
            self._close_line.setVisible(dense)
        self._request_history(first)

    def _request_history(self, first: int) -> None:
        if self._history.should_request(self._bars, first):
            self.history_needed.emit()

    def allow_history_request(self) -> None:
        self._history.allow()

    def set_ma_visible(self, visible: bool) -> None:
        self._ma_visible = visible
        for item in self._ma_items.values():
            item.setVisible(visible)
        self._refresh_info()

    def set_boll_visible(self, visible: bool) -> None:
        self.boll.set_visible(visible)
        self._refresh_info()

    def set_indicator(self, kind: str) -> None:
        self.indicator.set_kind(kind)
        if self._bars is not None:
            left, right = self.price.getViewBox().viewRange()[0]
            self.indicator.sync_y_range(
                max(0, int(np.floor(left))),
                min(len(self._bars) - 1, int(np.ceil(right))),
            )
        self._refresh_info()

    def export_png(self, path: str) -> bool:
        return self.grab().save(path)

    def eventFilter(self, watched: object, event: QEvent) -> bool:
        if watched is self.glw.viewport() and event.type() == QEvent.Type.Leave:
            self._hide_crosshair()
        return super().eventFilter(watched, event)

    def _on_mouse(self, position: object) -> None:
        if self._bars is None:
            return
        in_price = self.price.sceneBoundingRect().contains(position)
        in_volume = self.volume.sceneBoundingRect().contains(position)
        in_indicator = self.indicator.plot.sceneBoundingRect().contains(position)
        if not (in_price or in_volume or in_indicator):
            self._hide_crosshair()
            return
        point = self.price.getViewBox().mapSceneToView(position)
        index = int(round(point.x()))
        if index < 0 or index >= len(self._bars):
            self._hide_crosshair()
            return
        self._hover_index = index
        self.crosshair.show(index, point.y() if in_price else None)
        self._update_info(index)

    def _hide_crosshair(self) -> None:
        self.crosshair.hide()
        self._hover_index = None
        if self._bars is not None:
            self._update_info(len(self._bars) - 1)

    def _refresh_info(self) -> None:
        if self._bars is None:
            return
        index = self._hover_index
        if index is None:
            index = len(self._bars) - 1
        self._update_info(index)

    def _update_info(self, index: int) -> None:
        if self._bars is None or index < 0 or index >= len(self._bars):
            return
        self.info.update(
            self._bars,
            index,
            ma_values=self._ma_values,
            ma_visible=self._ma_visible,
            boll_values=self.boll.values(index),
            indicator_values=self.indicator.values(index),
            volume_factor=self._volume_factor,
            volume_unit=self._volume_unit,
        )
