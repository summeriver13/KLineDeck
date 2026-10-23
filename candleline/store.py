"""自选股持久化：JSON 存放在系统配置目录。"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from PySide6.QtCore import QStandardPaths

from .data import Stock


def config_dir() -> Path:
    base = QStandardPaths.writableLocation(QStandardPaths.AppConfigLocation)
    path = Path(base) if base else Path.home() / ".candleline"
    path.mkdir(parents=True, exist_ok=True)
    return path


class Watchlist:
    def __init__(self) -> None:
        self.path = config_dir() / "watchlist.json"
        self._items: list[Stock] = self._load()

    @property
    def items(self) -> list[Stock]:
        return list(self._items)

    def contains(self, code: str) -> bool:
        return any(stock.code == code for stock in self._items)

    def add(self, stock: Stock) -> bool:
        if self.contains(stock.code):
            return False
        self._items.append(stock)
        self._save()
        return True

    def remove(self, code: str) -> bool:
        kept = [stock for stock in self._items if stock.code != code]
        if len(kept) == len(self._items):
            return False
        self._items = kept
        self._save()
        return True

    def _load(self) -> list[Stock]:
        try:
            raw = json.loads(self.path.read_text("utf-8"))
        except (OSError, ValueError):
            return []
        items: list[Stock] = []
        for record in raw:
            try:
                items.append(Stock(**record))
            except TypeError:
                continue
        return items

    def _save(self) -> None:
        payload = [asdict(stock) for stock in self._items]
        self.path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), "utf-8"
        )
