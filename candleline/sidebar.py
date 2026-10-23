"""左侧边栏：搜索、结果与自选股。"""

from __future__ import annotations

from PySide6.QtCore import QPoint, Qt, QThreadPool, QTimer, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QVBoxLayout,
    QWidget,
)

from . import data
from .data import Stock
from .store import Watchlist
from .tasks import Dispatcher, Worker


class Sidebar(QFrame):
    stockActivated = Signal(object)
    watchlistChanged = Signal()

    def __init__(self, watchlist: Watchlist, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(288)
        self._watchlist = watchlist
        self._current: Stock | None = None
        self._search_token = 0
        self._dispatch = Dispatcher(self)
        self._dispatch.done.connect(self._search_ok)
        self._dispatch.failed.connect(self._search_fail)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(350)
        self._timer.timeout.connect(self._search)
        self._build()
        self._refresh_watchlist()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 18, 16, 14)
        layout.setSpacing(8)

        brand = QLabel("CandleLine")
        brand.setObjectName("brand")
        subtitle = QLabel("A 股行情终端")
        subtitle.setObjectName("subtitle")
        layout.addWidget(brand)
        layout.addWidget(subtitle)
        layout.addSpacing(10)

        self.search = QLineEdit()
        self.search.setPlaceholderText("搜索 A 股代码或名称")
        self.search.setToolTip("仅支持 A 股与 A 股指数，回车加载第一个结果")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._on_text)
        self.search.returnPressed.connect(self._load_first)
        layout.addWidget(self.search)

        self.results = QListWidget()
        self.results.setFixedHeight(0)
        self.results.hide()
        self.results.itemDoubleClicked.connect(self._activate_item)
        self.results.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.results.customContextMenuRequested.connect(self._result_menu)
        layout.addWidget(self.results)

        self.hint = QLabel("输入至少 2 个字符开始搜索")
        self.hint.setObjectName("hint")
        self.hint.setWordWrap(True)
        layout.addWidget(self.hint)

        header = QHBoxLayout()
        header.setSpacing(6)
        self.section = QLabel("自选")
        self.section.setObjectName("section")
        manage = QLabel("右键管理")
        manage.setObjectName("hint")
        header.addWidget(self.section)
        header.addStretch(1)
        header.addWidget(manage)
        layout.addLayout(header)

        self.watchlist = QListWidget()
        self.watchlist.setToolTip("双击加载，右键管理")
        self.watchlist.itemDoubleClicked.connect(self._activate_item)
        self.watchlist.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.watchlist.customContextMenuRequested.connect(self._watch_menu)
        self.empty = QLabel("暂无自选\n搜索后点行情头部 ☆ 加入自选")
        self.empty.setObjectName("empty")
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty.setWordWrap(True)
        layout.addWidget(self.empty, 1)
        layout.addWidget(self.watchlist, 1)

        footer = QLabel("数据 Baostock · 仅供学习，不构成投资建议")
        footer.setObjectName("footer")
        footer.setWordWrap(True)
        layout.addWidget(footer)

    def set_current(self, stock: Stock) -> None:
        self._current = stock
        for row in range(self.watchlist.count()):
            item = self.watchlist.item(row)
            saved = item.data(Qt.ItemDataRole.UserRole)
            if saved is not None and saved.code == stock.code:
                self.watchlist.setCurrentItem(item)
                return
        self.watchlist.clearSelection()

    def _on_text(self, text: str) -> None:
        self.results.clear()
        self.results.hide()
        if len(text.strip()) >= 2:
            self.hint.setText("正在等待输入完成…")
            self._timer.start()
        else:
            self._timer.stop()
            self.hint.setText("输入至少 2 个字符开始搜索")

    def _search(self) -> None:
        keyword = self.search.text().strip()
        if len(keyword) < 2:
            return
        self._search_token += 1
        token = self._search_token
        self.hint.setText("搜索中…")
        worker = Worker(self._dispatch, token, data.search_stocks, keyword)
        QThreadPool.globalInstance().start(worker)

    def _search_ok(self, token: int, stocks: list[Stock]) -> None:
        if token != self._search_token:
            return
        self.results.clear()
        for stock in stocks:
            item = QListWidgetItem(f"{stock.name}   {stock.code}")
            item.setData(Qt.ItemDataRole.UserRole, stock)
            self.results.addItem(item)
        if stocks:
            self.results.setFixedHeight(min(220, len(stocks) * 32 + 4))
            self.results.show()
        else:
            self.results.hide()
        self.hint.setText(
            f"找到 {len(stocks)} 个结果，双击加载 · 右键加自选"
            if stocks
            else "没有匹配的 A 股标的（港股/美股暂不支持）"
        )

    def _search_fail(self, token: int, message: str) -> None:
        if token != self._search_token:
            return
        self.results.clear()
        self.results.hide()
        self.hint.setText(f"搜索失败：{message}")

    def _load_first(self) -> None:
        if self.results.count() == 0:
            self._timer.stop()
            self._search()
            return
        self._activate_item(self.results.item(0))

    def _activate_item(self, item: QListWidgetItem) -> None:
        stock = item.data(Qt.ItemDataRole.UserRole)
        if stock is not None:
            self.stockActivated.emit(stock)

    def is_watched(self, code: str) -> bool:
        return self._watchlist.contains(code)

    def toggle_current(self) -> None:
        if self._current is None:
            self.hint.setText("先选择一只标的")
            return
        self._toggle(self._current)

    def _toggle(self, stock: Stock) -> None:
        if self._watchlist.remove(stock.code):
            message = f"已移除：{stock.name}"
        elif self._watchlist.add(stock):
            message = f"已加入自选：{stock.name}"
        else:
            return
        self.hint.setText(message)
        self._refresh_watchlist()
        if self._current is not None:
            self.set_current(self._current)
        self.watchlistChanged.emit()

    def _result_menu(self, pos: QPoint) -> None:
        item = self.results.itemAt(pos)
        if item is None:
            return
        stock = item.data(Qt.ItemDataRole.UserRole)
        if stock is None:
            return
        menu = QMenu(self)
        load = menu.addAction("加载")
        toggle = menu.addAction(
            "移出自选" if self._watchlist.contains(stock.code) else "加入自选"
        )
        chosen = menu.exec(self.results.mapToGlobal(pos))
        if chosen == load:
            self.stockActivated.emit(stock)
        elif chosen == toggle:
            self._toggle(stock)

    def _watch_menu(self, pos: QPoint) -> None:
        item = self.watchlist.itemAt(pos)
        if item is None:
            return
        stock = item.data(Qt.ItemDataRole.UserRole)
        if stock is None:
            return
        menu = QMenu(self)
        load = menu.addAction("加载")
        remove = menu.addAction("移出自选")
        chosen = menu.exec(self.watchlist.mapToGlobal(pos))
        if chosen == load:
            self.stockActivated.emit(stock)
        elif chosen == remove:
            self._toggle(stock)

    def _refresh_watchlist(self) -> None:
        self.watchlist.clear()
        for stock in self._watchlist.items:
            item = QListWidgetItem(f"{stock.name}   {stock.code}")
            item.setData(Qt.ItemDataRole.UserRole, stock)
            item.setToolTip("双击加载，右键管理")
            self.watchlist.addItem(item)
        count = len(self._watchlist.items)
        self.section.setText(f"自选 · {count}" if count else "自选")
        self.watchlist.setVisible(count > 0)
        self.empty.setVisible(count == 0)
