"""pyqtgraph 图元：蜡烛、日期轴与均线计算。"""

from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QColor, QPainter, QPen, QPicture

from .indicators import sma

NICE_STEPS = (1, 2, 5, 10, 20, 25, 50, 100, 200, 250, 500, 1000)


def moving_average(values: np.ndarray, window: int) -> np.ndarray:
    return sma(values, window)


def _nice_step(raw: int) -> int:
    for step in NICE_STEPS:
        if step >= raw:
            return step
    return raw


class CandleItem(pg.GraphicsObject):
    """用 QPicture 缓存的蜡烛图，避免每帧重绘上千根 K 线。"""

    def __init__(
        self,
        open_: np.ndarray,
        high: np.ndarray,
        low: np.ndarray,
        close: np.ndarray,
        up_color: str,
        down_color: str,
        width: float = 0.72,
    ) -> None:
        super().__init__()
        self._open = open_
        self._high = high
        self._low = low
        self._close = close
        self._up = QColor(up_color)
        self._down = QColor(down_color)
        self._width = width
        self._picture = QPicture()
        self._paint()

    def _paint(self) -> None:
        painter = QPainter(self._picture)
        half = self._width / 2
        for index in range(len(self._close)):
            open_price = self._open[index]
            close_price = self._close[index]
            if np.isnan(open_price) or np.isnan(close_price):
                continue
            color = self._up if close_price >= open_price else self._down
            painter.setPen(QPen(color, 0))
            painter.drawLine(
                QPointF(index, self._low[index]),
                QPointF(index, self._high[index]),
            )
            top = max(open_price, close_price)
            bottom = min(open_price, close_price)
            if top - bottom < 1e-9:
                painter.drawLine(QPointF(index - half, top), QPointF(index + half, top))
            else:
                painter.setBrush(color)
                painter.drawRect(QRectF(index - half, bottom, self._width, top - bottom))

    def paint(self, painter: QPainter, *args: object) -> None:
        painter.drawPicture(0, 0, self._picture)

    def boundingRect(self) -> QRectF:
        if len(self._close) == 0:
            return QRectF()
        low = float(np.nanmin(self._low))
        high = float(np.nanmax(self._high))
        return QRectF(-1, low, len(self._close) + 1, max(high - low, 1e-6))


class DateAxis(pg.AxisItem):
    """x 轴是 K 线下标，这里把下标映射回真实的交易日期。"""

    def __init__(self, **kwargs: object) -> None:
        super().__init__(orientation="bottom", **kwargs)
        self._dates: np.ndarray | None = None

    def set_dates(self, dates: np.ndarray) -> None:
        self._dates = dates
        self.picture = None
        self.update()

    def tickValues(self, minVal: float, maxVal: float, size: float) -> list:
        if self._dates is None or len(self._dates) == 0:
            return []
        first = max(0, int(np.floor(minVal)))
        last = min(len(self._dates) - 1, int(np.ceil(maxVal)))
        if last < first:
            return []
        span = last - first + 1
        target = max(2, int(size / 120))
        step = _nice_step(max(1, span // target))
        start = first + (step - first % step) % step
        values = [float(value) for value in range(start, last + 1, step)]
        return [(step, values)] if values else []

    def tickStrings(self, values: list[float], scale: float, spacing: float) -> list[str]:
        if self._dates is None:
            return ["" for _ in values]
        labels: list[str] = []
        for value in values:
            index = int(round(value))
            if index < 0 or index >= len(self._dates):
                labels.append("")
                continue
            day = self._dates[index]
            year = int(day.astype("datetime64[Y]").astype(int)) + 1970
            month = int(day.astype("datetime64[M]").astype(int)) % 12 + 1
            day_of_month = int((day - day.astype("datetime64[M]")).astype(int)) + 1
            if spacing >= 240:
                labels.append(f"{year}")
            elif spacing >= 20:
                labels.append(f"{year}-{month:02d}")
            else:
                labels.append(f"{month:02d}-{day_of_month:02d}")
        return labels
