"""行情信息栏：主行 OHLC 与副行 MA/BOLL/指标读数。"""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QSizePolicy, QVBoxLayout, QWidget

from .data import Bars
from .theme import DOWN, MA_COLORS, MUTED, UP


class InfoBar(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("infoPanel")
        self.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred
        )
        self.main = QLabel()
        self.main.setObjectName("info")
        self.main.setTextFormat(Qt.TextFormat.RichText)
        self.main.setWordWrap(True)
        self.main.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        self.ma_detail = self._build_detail()
        self.boll_detail = self._build_detail()
        self.signal_detail = self._build_detail()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 7, 10, 7)
        layout.setSpacing(2)
        layout.addWidget(self.main)
        layout.addWidget(self.ma_detail)
        layout.addWidget(self.boll_detail)
        layout.addWidget(self.signal_detail)
        self.waiting()

    @staticmethod
    def _build_detail() -> QLabel:
        label = QLabel()
        label.setObjectName("detail")
        label.setTextFormat(Qt.TextFormat.RichText)
        label.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed
        )
        return label

    def waiting(self, text: str = "等待行情数据…") -> None:
        self.main.setText(f'<span style="color:{MUTED}">{text}</span>')
        self.ma_detail.hide()
        self.boll_detail.hide()
        self.signal_detail.hide()

    def update(
        self,
        bars: Bars,
        index: int,
        *,
        ma_values: dict[int, np.ndarray],
        ma_visible: bool,
        boll_values: list[tuple[str, str, str]],
        indicator_values: list[tuple[str, str, str]],
        volume_factor: float,
        volume_unit: str,
    ) -> None:
        change = bars.pct_chg[index]
        if not np.isfinite(change):
            previous = bars.preclose[index]
            if np.isfinite(previous) and previous > 0:
                change = (bars.close[index] / previous - 1.0) * 100.0
            else:
                change = 0.0
        color = UP if change >= 0 else DOWN
        volume = bars.volume[index] / volume_factor
        turn = bars.turn[index]
        turn_text = "—" if np.isnan(turn) else f"{turn:.2f}%"
        parts = [
            f'<span style="color:{MUTED}">{bars.dates[index]}</span>',
            f'开&nbsp;<span style="color:{color}">{bars.open[index]:.2f}</span>',
            f'高&nbsp;<span style="color:{color}">{bars.high[index]:.2f}</span>',
            f'低&nbsp;<span style="color:{color}">{bars.low[index]:.2f}</span>',
            f'收&nbsp;<span style="color:{color}">{bars.close[index]:.2f}</span>',
            f'<span style="color:{color}">{change:+.2f}%</span>',
            f'量&nbsp;<span style="color:{color}">{volume:.2f}{volume_unit}</span>',
            f"换手&nbsp;{turn_text}",
        ]
        self.main.setText(" ".join(parts))

        ma_parts: list[str] = []
        if ma_visible:
            for period, ma_color in MA_COLORS.items():
                value = ma_values[period][index]
                if np.isfinite(value):
                    ma_parts.append(
                        f'<span style="color:{ma_color}">MA{period} {value:.2f}</span>'
                    )
        self._set_detail(self.ma_detail, ma_parts)
        boll_parts = [
            f'<span style="color:{value_color}">{label} {text}</span>'
            for label, value_color, text in boll_values
        ]
        self._set_detail(self.boll_detail, boll_parts)
        signal_parts = [
            f'<span style="color:{value_color}">{label} {text}</span>'
            for label, value_color, text in indicator_values
        ]
        self._set_detail(self.signal_detail, signal_parts)

    @staticmethod
    def _set_detail(label: QLabel, parts: list[str]) -> None:
        if parts:
            label.setText("&nbsp;&nbsp;".join(parts))
            label.show()
        else:
            label.hide()
