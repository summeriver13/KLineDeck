"""主窗口：工具栏、侧栏、行情头部与 K 线图。"""

from __future__ import annotations

import pyqtgraph as pg
from PySide6.QtCore import QThreadPool
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QFileDialog, QMainWindow, QMessageBox

from . import data
from .chart import ChartWidget
from .data import ADJUST_LABELS, FREQ_LABELS, Bars, Stock
from .header import Header
from .sidebar import Sidebar
from .store import Watchlist
from .tasks import Dispatcher, Worker
from .theme import BG, MUTED
from .toolbar import build_toolbar
from .window_layout import build_central, build_status


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        pg.setConfigOptions(background=BG, foreground=MUTED, antialias=True)
        self.setWindowTitle("KLineDeck · A 股行情终端")
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
        self._full_after_older = False
        self._full_dispatch = Dispatcher(self)
        self._full_dispatch.done.connect(self._full_ok)
        self._full_dispatch.failed.connect(self._full_fail)
        self._older_token = 0
        self._older_pending = False
        self._older_dispatch = Dispatcher(self)
        self._older_dispatch.done.connect(self._older_ok)
        self._older_dispatch.failed.connect(self._older_fail)
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
            on_boll=self.chart.set_boll_visible,
            on_indicator=self.chart.set_indicator,
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
        self.chart.history_needed.connect(self._load_older)
        self.header = Header()
        self.sidebar.watchlistChanged.connect(self._sync_watch)
        self.header.watchToggled.connect(self.sidebar.toggle_current)
        self.setCentralWidget(build_central(self.sidebar, self.chart, self.header))
        self.status, self.busy, self.source = build_status(
            self, data.source_name().title()
        )

    def _install_shortcuts(self) -> None:
        shortcut = QShortcut(QKeySequence.StandardKey.Find, self)
        shortcut.activated.connect(self._focus_search)

    def _focus_search(self) -> None:
        self.sidebar.search.setFocus()
        self.sidebar.search.selectAll()

    def _load_stock(self, stock: Stock) -> None:
        self._stock = stock
        self.sidebar.set_current(stock)
        self.header.set_stock(stock)
        self._sync_watch()
        self._reload()

    def _sync_watch(self) -> None:
        self.header.set_watched(self.sidebar.is_watched(self._stock.code))

    def _reload(self) -> None:
        self._full_token += 1
        self._full_pending = False
        self._full_after_older = False
        self._older_token += 1
        self._older_pending = False
        key = (self._stock.code, self._freq, self._adjust)
        cached = self._cache.get(key)
        if cached is not None:
            if self._range == "all" and not cached.full:
                self._load_full_history()
            self._render(cached)
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
        if self._range == "all" and not bars.full:
            self._load_full_history()
        self._render(bars)

    def _bars_fail(self, token: int, message: str) -> None:
        if token != self._bars_token:
            return
        self._set_busy(None)
        self.status.setText("加载失败")
        QMessageBox.warning(self, "加载失败", message)

    def _render(self, bars: Bars, preserve_view: bool = False) -> None:
        self.chart.set_bars(bars, preserve_view=preserve_view)
        self.header.set_quote(self._stock, bars)
        self.setWindowTitle(f"{self._stock.name} {bars.code} · KLineDeck")
        hint = "滚轮缩放，拖拽平移"
        if not bars.full:
            hint += "，向左自动补历史"
        self.status.setText(
            f"{len(bars)} 根 · {bars.dates[0]} ~ {bars.dates[-1]} · {hint}"
        )
        source = data.source_name().title()
        self.source.setText(
            f"{FREQ_LABELS[bars.freq]} · {ADJUST_LABELS[bars.adjust]} · {source}"
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
        bars = self.chart.bars
        if key == "all" and bars is not None and not bars.full:
            self._load_full_history()
        self.chart.set_range(key)

    def _load_full_history(self) -> None:
        if self._full_pending:
            return
        if self._older_pending:
            self._full_after_older = True
            return
        self._full_after_older = False
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
        self._full_after_older = False
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
        self._full_after_older = False
        self._set_busy(None)
        self.status.setText(f"完整历史加载失败：{message}")
        self.chart.allow_history_request()

    def _load_older(self) -> None:
        bars = self.chart.bars
        if bars is None or bars.full or self._full_pending or self._older_pending:
            return
        if (bars.code, bars.freq, bars.adjust) != (
            self._stock.code,
            self._freq,
            self._adjust,
        ):
            return
        self._older_pending = True
        self._older_token += 1
        token = self._older_token
        self._set_busy(f"正在补充 {self._stock.name} 更早的 K 线…")
        worker = Worker(
            self._older_dispatch,
            token,
            data.fetch_older,
            bars,
        )
        QThreadPool.globalInstance().start(worker)

    def _older_ok(self, token: int, bars: Bars) -> None:
        if token != self._older_token:
            return
        pending_full = self._full_after_older
        self._full_after_older = False
        self._older_pending = False
        self._set_busy(None)
        self._cache[(bars.code, bars.freq, bars.adjust)] = bars
        if pending_full and self._range == "all" and not bars.full:
            self._load_full_history()
        self._render(bars, preserve_view=True)

    def _older_fail(self, token: int, message: str) -> None:
        if token != self._older_token:
            return
        pending_full = self._full_after_older
        self._full_after_older = False
        self._older_pending = False
        self._set_busy(None)
        self.status.setText(f"补充历史失败：{message}")
        if pending_full and self._range == "all":
            self._load_full_history()
        else:
            self.chart.allow_history_request()

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
