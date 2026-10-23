"""左侧边栏：搜索、结果与自选股。"""

from __future__ import annotations

from PySide6.QtCore import Qt, QThreadPool, QTimer, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from . import data
from .data import Stock
from .store import Watchlist
from .tasks import Dispatcher, Worker


class Sidebar(QFrame):
    stockActivated = Signal(object)

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
        self.search.setPlaceholderText("搜索代码或名称，如 600000 / 浦发")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._on_text)
        self.search.returnPressed.connect(self._load_first)
        layout.addWidget(self.search)

        self.results = QListWidget()
        self.results.setMaximumHeight(220)
        self.results.itemDoubleClicked.connect(self._activate_item)
        layout.addWidget(self.results)

        self.hint = QLabel("输入至少 2 个字符开始搜索")
        self.hint.setObjectName("hint")
        self.hint.setWordWrap(True)
        layout.addWidget(self.hint)

        header = QHBoxLayout()
        header.setSpacing(6)
        section = QLabel("自选")
        section.setObjectName("section")
        add_button = QPushButton("+")
        add_button.setFixedSize(28, 24)
        add_button.setToolTip("把当前标的加入自选")
        add_button.clicked.connect(self._add_current)
        remove_button = QPushButton("−")
        remove_button.setFixedSize(28, 24)
        remove_button.setToolTip("从自选移除选中项")
        remove_button.clicked.connect(self._remove_selected)
        header.addWidget(section)
        header.addStretch(1)
        header.addWidget(add_button)
        header.addWidget(remove_button)
        layout.addLayout(header)

        self.watchlist = QListWidget()
        self.watchlist.itemDoubleClicked.connect(self._activate_item)
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
        self.hint.setText(f"找到 {len(stocks)} 个结果，双击加载" if stocks else "没有匹配结果")

    def _search_fail(self, token: int, message: str) -> None:
        if token != self._search_token:
            return
        self.results.clear()
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

    def _add_current(self) -> None:
        if self._current is None:
            self.hint.setText("先选择一只标的")
            return
        if self._watchlist.add(self._current):
            self.hint.setText(f"已加入自选：{self._current.name}")
        else:
            self.hint.setText("该标的已在自选中")
        self._refresh_watchlist()
        self.set_current(self._current)

    def _remove_selected(self) -> None:
        item = self.watchlist.currentItem()
        if item is None:
            self.hint.setText("先选中一个自选项")
            return
        stock = item.data(Qt.ItemDataRole.UserRole)
        if stock is not None and self._watchlist.remove(stock.code):
            self.hint.setText(f"已移除：{stock.name}")
        self._refresh_watchlist()

    def _refresh_watchlist(self) -> None:
        self.watchlist.clear()
        for stock in self._watchlist.items:
            item = QListWidgetItem(f"{stock.name}   {stock.code}")
            item.setData(Qt.ItemDataRole.UserRole, stock)
            self.watchlist.addItem(item)
