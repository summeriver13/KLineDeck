"""主工具栏：周期、复权、区间、均线与导出。"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import QComboBox, QLabel, QMainWindow, QToolBar

from .chart_view import RANGE_LABELS
from .data import ADJUST_LABELS


def build_toolbar(
    window: QMainWindow,
    *,
    freq: str,
    adjust: str,
    range_key: str,
    on_freq: Callable[[str], None],
    on_adjust: Callable[[str], None],
    on_range: Callable[[str], None],
    on_ma: Callable[[bool], None],
    on_boll: Callable[[bool], None],
    on_indicator: Callable[[str], None],
    on_export: Callable[[], None],
) -> QAction:
    toolbar = QToolBar("main")
    toolbar.setObjectName("main")
    toolbar.setMovable(False)
    window.addToolBar(toolbar)
    _add_group(
        toolbar, window, "周期",
        [("d", "日K"), ("w", "周K"), ("m", "月K")], freq, on_freq,
    )
    _add_combo(toolbar, "复权", list(ADJUST_LABELS.items()), adjust, on_adjust)
    _add_combo(
        toolbar, "区间", list(RANGE_LABELS.items()), range_key, on_range
    )
    ma_action = QAction("均线", window)
    ma_action.setCheckable(True)
    ma_action.setChecked(True)
    ma_action.setToolTip("叠加 MA5 / MA10 / MA20 / MA60")
    ma_action.triggered.connect(on_ma)
    toolbar.addAction(ma_action)
    boll_action = QAction("BOLL", window)
    boll_action.setCheckable(True)
    boll_action.setToolTip("叠加布林带（20, 2）")
    boll_action.triggered.connect(on_boll)
    toolbar.addAction(boll_action)
    toolbar.addSeparator()

    _add_combo(
        toolbar,
        "副图",
        [("macd", "MACD"), ("kdj", "KDJ"), ("rsi", "RSI")],
        "macd",
        on_indicator,
    )

    export = QAction("导出 PNG", window)
    export.triggered.connect(on_export)
    toolbar.addAction(export)
    return ma_action


def _add_combo(
    toolbar: QToolBar,
    title: str,
    options: list[tuple[str, str]],
    current: str,
    callback: Callable[[str], None],
) -> None:
    label = QLabel(title)
    label.setObjectName("hint")
    toolbar.addWidget(label)
    combo = QComboBox()
    combo.setObjectName("indicator")
    for key, text in options:
        combo.addItem(text, key)
    index = combo.findData(current)
    combo.setCurrentIndex(max(0, index))
    combo.currentIndexChanged.connect(
        lambda selected: callback(combo.itemData(selected))
    )
    toolbar.addWidget(combo)
    toolbar.addSeparator()


def _add_group(
    toolbar: QToolBar,
    window: QMainWindow,
    title: str,
    options: list[tuple[str, str]],
    current: str,
    callback: Callable[[str], None],
) -> None:
    label = QLabel(title)
    label.setObjectName("hint")
    toolbar.addWidget(label)
    group = QActionGroup(window)
    group.setExclusive(True)
    for key, text in options:
        action = QAction(text, window)
        action.setCheckable(True)
        action.setData(key)
        action.triggered.connect(lambda checked=False, k=key: callback(k))
        group.addAction(action)
        toolbar.addAction(action)
        if key == current:
            action.setChecked(True)
    toolbar.addSeparator()
