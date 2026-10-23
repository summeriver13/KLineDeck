"""K 线图控件：蜡烛、成交量、均线、十字光标与区间缩放。"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QLabel, QSizePolicy, QVBoxLayout, QWidget

from .data import Bars
from .items import CandleItem, DateAxis, moving_average
from .theme import BG, BORDER, DOWN, FAINT, GRID, MA_COLORS, MUTED, TEXT, UP

MA_PERIODS = tuple(MA_COLORS)
RANGE_DAYS = {"1m": 30, "3m": 90, "6m": 180, "1y": 365, "3y": 1095, "all": None}
RANGE_LABELS = {"1m": "1月", "3m": "3月", "6m": "6月", "1y": "1年", "3y": "3年", "all": "全部"}


class ChartWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._bars: Bars | None = None
        self._candle: CandleItem | None = None
        self._volume_bars: pg.BarGraphItem | None = None
        self._ma_items: dict[int, pg.PlotDataItem] = {}
        self._ma_values: dict[int, np.ndarray] = {}
        self._last_line: pg.InfiniteLine | None = None
        self._ma_visible = True
        self._range_key = "1y"
        self._volume_factor = 1e6
        self._volume_unit = "万手"

        self.info = QLabel()
        self.info.setObjectName("info")
        self.info.setTextFormat(Qt.TextFormat.RichText)
        self.info.setText("等待行情数据…")
        self.info.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed
        )

        self.glw = pg.GraphicsLayoutWidget()
        self.glw.setBackground(BG)
        self.price = self.glw.addPlot(row=0, col=0)
        self.volume = self.glw.addPlot(row=1, col=0)
        self.glw.ci.layout.setRowStretchFactor(0, 4)
        self.glw.ci.layout.setRowStretchFactor(1, 1)

        self._configure_plot(self.price, bottom=False)
        self._configure_plot(self.volume, bottom=True)
        self.price.hideAxis("bottom")
        self.price.showAxis("right")
        self.price.hideAxis("left")
        self.volume.showAxis("right")
        self.volume.hideAxis("left")
        self.price.getAxis("right").setWidth(64)
        self.volume.getAxis("right").setWidth(64)
        self.volume.setXLink(self.price)
        self.price.getViewBox().sigXRangeChanged.connect(self._sync_y_range)

        self.date_axis = DateAxis()
        self.volume.setAxisItems({"bottom": self.date_axis})

        pen = pg.mkPen("#5b6b82", width=1, style=Qt.PenStyle.DashLine)
        self.vline = pg.InfiniteLine(angle=90, movable=False, pen=pen)
        self.vline_volume = pg.InfiniteLine(angle=90, movable=False, pen=pen)
        self.hline = pg.InfiniteLine(angle=0, movable=False, pen=pen)
        for line in (self.vline, self.hline):
            self.price.addItem(line, ignoreBounds=True)
            line.setVisible(False)
        self.volume.addItem(self.vline_volume, ignoreBounds=True)
        self.vline_volume.setVisible(False)
        self.hline.label = pg.InfLineLabel(
            self.hline,
            text="",
            position=0.985,
            color=TEXT,
            fill=pg.mkBrush(QColor(20, 26, 36, 230)),
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 10)
        layout.setSpacing(6)
        layout.addWidget(self.info)
        layout.addWidget(self.glw, 1)

        self.glw.scene().sigMouseMoved.connect(self._on_mouse)
        self.glw.viewport().installEventFilter(self)

    @staticmethod
    def _configure_plot(plot: pg.PlotItem, bottom: bool) -> None:
        plot.setMenuEnabled(False)
        plot.hideButtons()
        plot.showGrid(x=False, y=True, alpha=0.12)
        plot.getViewBox().setMouseEnabled(x=True, y=False)
        plot.getViewBox().setDefaultPadding(0.02)

    @property
    def bars(self) -> Bars | None:
        return self._bars

    def set_bars(self, bars: Bars) -> None:
        self._bars = bars
        self._clear_items()
        x = np.arange(len(bars))

        self._candle = CandleItem(
            bars.open, bars.high, bars.low, bars.close, UP, DOWN
        )
        self._candle.setZValue(-10)
        self.price.addItem(self._candle)

        self._volume_factor = 1e8 if bars.is_index else 1e6
        self._volume_unit = "亿手" if bars.is_index else "万手"
        brushes = [
            pg.mkBrush(QColor(UP if close >= open_ else DOWN))
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

        self._add_last_line(bars.close[-1])
        self.date_axis.set_dates(bars.dates)
        self.set_range(self._range_key)
        self._sync_y_range(None, self.price.getViewBox().viewRange()[0])
        self._update_info(len(bars) - 1)

    def _add_last_line(self, price: float) -> None:
        pen = pg.mkPen(FAINT, width=1, style=Qt.PenStyle.DotLine)
        line = pg.InfiniteLine(
            pos=price,
            angle=0,
            pen=pen,
            label=f"{price:.2f}",
            labelOpts={
                "position": 0.985,
                "color": TEXT,
                "fill": pg.mkBrush(QColor(20, 26, 36, 220)),
            },
        )
        self.price.addItem(line, ignoreBounds=True)
        self._last_line = line

    def _clear_items(self) -> None:
        if self._candle is not None:
            self.price.removeItem(self._candle)
            self._candle = None
        if self._volume_bars is not None:
            self.volume.removeItem(self._volume_bars)
            self._volume_bars = None
        for item in self._ma_items.values():
            self.price.removeItem(item)
        self._ma_items.clear()
        self._ma_values.clear()
        if self._last_line is not None:
            self.price.removeItem(self._last_line)
            self._last_line = None

    def set_range(self, key: str) -> None:
        self._range_key = key
        if self._bars is None or len(self._bars) == 0:
            return
        days = RANGE_DAYS.get(key)
        last = len(self._bars) - 1
        if days is None:
            start = 0
        else:
            cutoff = self._bars.dates[-1] - np.timedelta64(days, "D")
            start = int(np.searchsorted(self._bars.dates, cutoff))
        view = self.price.getViewBox()
        view.setXRange(max(0, start - 1), last + 1, padding=0)

    def _sync_y_range(self, view: object, x_range: Sequence[float]) -> None:
        """把 y 轴锁到当前可见的 K 线上，滚轮/拖拽后同样生效。"""
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
        self.volume.getViewBox().setYRange(0, max(volume * 1.12, 1e-9), padding=0)

    def set_ma_visible(self, visible: bool) -> None:
        self._ma_visible = visible
        for item in self._ma_items.values():
            item.setVisible(visible)
        if self._bars is not None:
            self._update_info(len(self._bars) - 1)

    def export_png(self, path: str) -> bool:
        return self.grab().save(path)

    def eventFilter(self, watched: object, event: QEvent) -> bool:
        if watched is self.glw.viewport() and event.type() == QEvent.Type.Leave:
            self._hide_crosshair()
        return super().eventFilter(watched, event)

    def _on_mouse(self, position: object) -> None:
        if self._bars is None:
            return
        if not self.price.sceneBoundingRect().contains(position):
            self._hide_crosshair()
            return
        point = self.price.getViewBox().mapSceneToView(position)
        index = int(round(point.x()))
        if index < 0 or index >= len(self._bars):
            self._hide_crosshair()
            return
        self.vline.setPos(index)
        self.vline_volume.setPos(index)
        self.hline.setPos(point.y())
        self.vline.setVisible(True)
        self.vline_volume.setVisible(True)
        self.hline.setVisible(True)
        self.hline.label.setText(f"{point.y():.2f}")
        self._update_info(index)

    def _hide_crosshair(self) -> None:
        self.vline.setVisible(False)
        self.vline_volume.setVisible(False)
        self.hline.setVisible(False)
        if self._bars is not None:
            self._update_info(len(self._bars) - 1)

    def _update_info(self, index: int) -> None:
        if self._bars is None or index < 0 or index >= len(self._bars):
            return
        bars = self._bars
        change = bars.pct_chg[index]
        color = UP if change >= 0 else DOWN
        volume = bars.volume[index] / self._volume_factor
        turn = bars.turn[index]
        turn_text = "—" if np.isnan(turn) else f"{turn:.2f}%"
        parts = [
            f'<span style="color:{MUTED}">{bars.dates[index]}</span>',
            f'开 <span style="color:{color}">{bars.open[index]:.2f}</span>',
            f'高 <span style="color:{color}">{bars.high[index]:.2f}</span>',
            f'低 <span style="color:{color}">{bars.low[index]:.2f}</span>',
            f'收 <span style="color:{color}">{bars.close[index]:.2f}</span>',
            f'<span style="color:{color}">{change:+.2f}%</span>',
            f'量 <span style="color:{color}">{volume:.2f}{self._volume_unit}</span>',
            f"换手 {turn_text}",
        ]
        if self._ma_visible:
            for period, ma_color in MA_COLORS.items():
                value = self._ma_values[period][index]
                if not np.isnan(value):
                    parts.append(
                        f'<span style="color:{ma_color}">MA{period} {value:.2f}</span>'
                    )
        self.info.setText("&nbsp;&nbsp;".join(parts))
