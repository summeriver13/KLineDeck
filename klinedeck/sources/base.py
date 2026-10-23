"""行情数据源接口：新增数据源只需实现这三件事。"""

from __future__ import annotations

from typing import Protocol

from ..models import Bars, Stock


class MarketDataSource(Protocol):
    name: str

    def full_start(self, freq: str) -> str:
        """该周期可取到的最早日期，ISO 格式。"""
        ...

    def search(self, keyword: str) -> list[Stock]:
        """按名称搜索标的。"""
        ...

    def fetch(
        self,
        code: str,
        freq: str,
        adjust: str,
        is_index: bool,
        start: str,
        end: str | None = None,
    ) -> Bars:
        """取 start 到 end 的复权 K 线，按日期升序；end 为空表示到最新。"""
        ...
