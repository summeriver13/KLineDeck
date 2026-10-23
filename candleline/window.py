"""主窗口：工具栏、侧栏、行情头部与 K 线图。"""

from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt, QThreadPool
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from . import data
from .chart import ChartWidget
from .data import ADJUST_LABELS, FREQ_LABELS, Bars, Stock
from .sidebar import Sidebar
from .store import Watchlist
from .tasks import Dispatcher, Worker
from .theme import BG, DOWN, MUTED, UP
from .toolbar import build_toolbar


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        pg.setConfigOptions(background=BG, foreground=MUTED, antialias=True)
        self.setWindowTitle("CandleLine · A 股行情终端")
        self.resize(1440, 900)
        self.setMinimumSize(1080, 680)

        self._freq = "d"
        self._adjust = "qfq"
        self._range = "1y"
        self._stock = Stock("sh.000001", "上证指数", True)
        self._cache: dict[tuple[str, str, str], Bars] = {}
        self._bars_token = 0
        self._dispatch = Dispatcher(self)
        self._dispatch.done.connect(self._bars_ok)
        self._dispatch.failed.connect(self._bars_fail)
        self._full_token = 0
        self._full_pending = False
        self._full_dispatch = Dispatcher(self)
        self._full_dispatch.done.connect(self._full_ok)
        self._full_dispatch.failed.connect(self._full_fail)
        self._watchlist = Watchlist()

        self._build()
        self.ma_action = build_toolbar(
            self,
            freq=self._freq,
            adjust=self._adjust,
            range_key=self._range,
            on_freq=self._set_freq,
            on_adjust=self._set_adjust,
            on_range=self._set_range,
            on_ma=self.chart.set_ma_visible,
            on_export=self._export,
        )
        self._install_shortcuts()
        start = (
            self._watchlist.items[0]
            if self._watchlist.items
            else Stock("sh.000001", "上证指数", True)
        )
        self._load_stock(start)

    def _build(self) -> None:
        self.sidebar = Sidebar(self._watchlist)
        self.sidebar.stockActivated.connect(self._load_stock)
        self.chart = ChartWidget()

        right = QWidget()
        layout = QVBoxLayout(right)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._build_header())
        layout.addWidget(self.chart, 1)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.sidebar)
        splitter.addWidget(right)
        splitter.setStretchFactor(1, 1)
        splitter.setChildrenCollapsible(False)
        self.setCentralWidget(splitter)

        status = self.statusBar()
        self.status = QLabel("就绪")
        self.busy = QProgressBar()
        self.busy.setRange(0, 0)
        self.busy.setFixedSize(90, 6)
        self.busy.setTextVisible(False)
        self.busy.hide()
        self.source = QLabel("Baostock")
        status.addWidget(self.status, 1)
        status.addPermanentWidget(self.busy)
        status.addPermanentWidget(self.source)

    def _build_header(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("header")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(16, 10, 16, 12)
        layout.setSpacing(10)

        self.name_label = QLabel("—")
        self.name_label.setObjectName("title")
        self.code_label = QLabel("")
        self.code_label.setObjectName("code")
        layout.addWidget(self.name_label)
        layout.addWidget(self.code_label, 0, Qt.AlignmentFlag.AlignBottom)
        layout.addStretch(1)

        self.price_label = QLabel("—")
        self.price_label.setObjectName("price")
        self.change_label = QLabel("")
        self.change_label.setObjectName("change")
        layout.addWidget(self.price_label)
        layout.addWidget(self.change_label, 0, Qt.AlignmentFlag.AlignBottom)
        return frame

    def _install_shortcuts(self) -> None:
        shortcut = QShortcut(QKeySequence.StandardKey.Find, self)
        shortcut.activated.connect(self._focus_search)

    def _focus_search(self) -> None:
        self.sidebar.search.setFocus()
        self.sidebar.search.selectAll()

    def _load_stock(self, stock: Stock) -> None:
        self._stock = stock
        self.sidebar.set_current(stock)
        self.name_label.setText(stock.name)
        self.code_label.setText(stock.code)
        self.price_label.setText("—")
        self.change_label.setText("")
        self._reload()

    def _reload(self) -> None:
        self._full_token += 1
        self._full_pending = False
        key = (self._stock.code, self._freq, self._adjust)
        cached = self._cache.get(key)
        if cached is not None:
            self._render(cached)
            if self._range == "all" and not cached.full:
                self._load_full_history()
            return
        self._bars_token += 1
        token = self._bars_token
        self._set_busy(f"正在加载 {self._stock.name} · {FREQ_LABELS[self._freq]}…")
        worker = Worker(
            self._dispatch,
            token,
            data.fetch_bars,
            self._stock.code,
            self._freq,
            self._adjust,
            self._stock.is_index,
        )
        QThreadPool.globalInstance().start(worker)

    def _bars_ok(self, token: int, bars: Bars) -> None:
        if token != self._bars_token:
            return
        self._cache[(bars.code, bars.freq, bars.adjust)] = bars
        self._set_busy(None)
        self._render(bars)
        if self._range == "all" and not bars.full:
            self._load_full_history()

    def _bars_fail(self, token: int, message: str) -> None:
        if token != self._bars_token:
            return
        self._set_busy(None)
        self.status.setText("加载失败")
        QMessageBox.warning(self, "加载失败", message)

    def _render(self, bars: Bars) -> None:
        self.chart.set_bars(bars)
        last = bars.close[-1]
        previous = bars.preclose[-1]
        if np.isnan(previous) and len(bars) > 1:
            previous = bars.close[-2]
        change = bars.pct_chg[-1]
        color = UP if change >= 0 else DOWN
        self.price_label.setText(f"{last:.2f}")
        self.price_label.setStyleSheet(f"color: {color};")
        if np.isnan(previous):
            self.change_label.setText(f"{change:+.2f}%")
        else:
            self.change_label.setText(f"{last - previous:+.2f}   {change:+.2f}%")
        self.change_label.setStyleSheet(f"color: {color};")
        self.name_label.setText(self._stock.name)
        self.code_label.setText(
            f"{bars.code} · {FREQ_LABELS[bars.freq]} · {ADJUST_LABELS[bars.adjust]}"
        )
        self.setWindowTitle(f"{self._stock.name} {bars.code} · CandleLine")
        self.status.setText(
            f"{len(bars)} 根 · {bars.dates[0]} ~ {bars.dates[-1]} · 滚轮缩放，拖拽平移"
        )
        self.source.setText(
            f"{FREQ_LABELS[bars.freq]} · {ADJUST_LABELS[bars.adjust]} · Baostock"
        )

    def _set_freq(self, key: str) -> None:
        if key == self._freq:
            return
        self._freq = key
        self._reload()

    def _set_adjust(self, key: str) -> None:
        if key == self._adjust:
            return
        self._adjust = key
        self._reload()

    def _set_range(self, key: str) -> None:
        self._range = key
        self.chart.set_range(key)
        bars = self.chart.bars
        if key == "all" and bars is not None and not bars.full:
            self._load_full_history()

    def _load_full_history(self) -> None:
        if self._full_pending:
            return
        self._full_pending = True
        self._full_token += 1
        self._set_busy(f"正在加载 {self._stock.name} 的全部历史…")
        worker = Worker(
            self._full_dispatch,
            self._full_token,
            data.fetch_bars,
            self._stock.code,
            self._freq,
            self._adjust,
            self._stock.is_index,
            True,
        )
        QThreadPool.globalInstance().start(worker)

    def _full_ok(self, token: int, bars: Bars) -> None:
        if token != self._full_token:
            return
        self._full_pending = False
        self._set_busy(None)
        if not bars.full:
            self.status.setText("完整历史暂不可用，已显示最近数据")
            return
        self._cache[(bars.code, bars.freq, bars.adjust)] = bars
        self._render(bars)

    def _full_fail(self, token: int, message: str) -> None:
        if token != self._full_token:
            return
        self._full_pending = False
        self._set_busy(None)
        self.status.setText(f"完整历史加载失败：{message}")

    def _set_busy(self, message: str | None) -> None:
        if message is None:
            self.busy.hide()
            return
        self.status.setText(message)
        self.busy.show()

    def _export(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "导出 K 线图",
            f"{self._stock.code}-{self._freq}.png",
            "PNG 图片 (*.png)",
        )
        if not path:
            return
        if self.chart.export_png(path):
            self.status.setText(f"已导出：{path}")
        else:
            QMessageBox.warning(self, "导出失败", "无法写入图片文件")
