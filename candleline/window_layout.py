"""主窗口中央区域与状态栏布局。"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel,
    QMainWindow,
    QProgressBar,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from .chart import ChartWidget
from .header import Header
from .sidebar import Sidebar


def build_central(
    sidebar: Sidebar,
    chart: ChartWidget,
    header: Header,
) -> QSplitter:
    right = QWidget()
    layout = QVBoxLayout(right)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)
    layout.addWidget(header)
    layout.addWidget(chart, 1)

    splitter = QSplitter(Qt.Orientation.Horizontal)
    splitter.addWidget(sidebar)
    splitter.addWidget(right)
    splitter.setStretchFactor(1, 1)
    splitter.setChildrenCollapsible(False)
    return splitter


def build_status(
    window: QMainWindow,
    source_name: str,
) -> tuple[QLabel, QProgressBar, QLabel]:
    status = window.statusBar()
    message = QLabel("就绪")
    busy = QProgressBar()
    busy.setRange(0, 0)
    busy.setFixedSize(90, 6)
    busy.setTextVisible(False)
    busy.hide()
    source = QLabel(source_name)
    status.addWidget(message, 1)
    status.addPermanentWidget(busy)
    status.addPermanentWidget(source)
    return message, busy, source
