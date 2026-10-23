"""主工具栏：周期、复权、区间、均线与导出。"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import QLabel, QMainWindow, QToolBar

from .chart import RANGE_LABELS


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
    _add_group(
        toolbar, window, "复权",
        [("qfq", "前复权"), ("hfq", "后复权"), ("none", "不复权")], adjust, on_adjust,
    )
    _add_group(
        toolbar, window, "区间", list(RANGE_LABELS.items()), range_key, on_range,
    )
    ma_action = QAction("MA", window)
    ma_action.setCheckable(True)
    ma_action.setChecked(True)
    ma_action.triggered.connect(on_ma)
    toolbar.addAction(ma_action)
    toolbar.addSeparator()
    export = QAction("导出 PNG", window)
    export.triggered.connect(on_export)
    toolbar.addAction(export)
    return ma_action


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
