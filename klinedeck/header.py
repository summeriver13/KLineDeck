"""行情头部：名称、代码、最新价与涨跌。"""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QToolButton, QWidget

from .data import ADJUST_LABELS, FREQ_LABELS, Bars, Stock
from .theme import DOWN, UP


class Header(QFrame):
    watchToggled = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("header")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 12)
        layout.setSpacing(10)

        self.name = QLabel("—")
        self.name.setObjectName("title")
        self.code = QLabel("")
        self.code.setObjectName("code")
        layout.addWidget(self.name)
        layout.addWidget(self.code, 0, Qt.AlignmentFlag.AlignBottom)
        self.watch = QToolButton()
        self.watch.setObjectName("watch")
        self.watch.setCursor(Qt.CursorShape.PointingHandCursor)
        self.watch.clicked.connect(self.watchToggled.emit)
        layout.addWidget(self.watch, 0, Qt.AlignmentFlag.AlignBottom)
        layout.addStretch(1)

        self.price = QLabel("—")
        self.price.setObjectName("price")
        self.change = QLabel("")
        self.change.setObjectName("change")
        layout.addWidget(self.price)
        layout.addWidget(self.change, 0, Qt.AlignmentFlag.AlignBottom)
        self.set_watched(False)

    def set_stock(self, stock: Stock) -> None:
        self.name.setText(stock.name)
        self.code.setText(stock.code)
        self.price.setText("—")
        self.price.setStyleSheet("")
        self.change.setText("")
        self.change.setStyleSheet("")
        self.set_watched(False)

    def set_watched(self, watched: bool) -> None:
        self.watch.setText("★ 自选" if watched else "☆ 自选")
        self.watch.setToolTip("从自选移除" if watched else "加入自选")
        self.watch.setProperty("watched", watched)
        self.watch.style().unpolish(self.watch)
        self.watch.style().polish(self.watch)

    def set_quote(self, stock: Stock, bars: Bars) -> None:
        last = float(bars.close[-1])
        previous = float(bars.preclose[-1])
        if np.isnan(previous) and len(bars) > 1:
            previous = float(bars.close[-2])
        change = float(bars.pct_chg[-1])
        color = UP if change >= 0 else DOWN
        self.price.setText(f"{last:.2f}")
        self.price.setStyleSheet(f"color: {color};")
        if np.isnan(previous):
            self.change.setText(f"{change:+.2f}%")
        else:
            self.change.setText(f"{last - previous:+.2f}   {change:+.2f}%")
        self.change.setStyleSheet(f"color: {color};")
        self.name.setText(stock.name)
        self.code.setText(
            f"{bars.code} · {FREQ_LABELS[bars.freq]} · {ADJUST_LABELS[bars.adjust]}"
        )
