"""本地 A 股目录：搜索走内存索引，不依赖 Baostock 网络。"""

from __future__ import annotations

import csv
from pathlib import Path

from .models import Stock

MAX_RESULTS = 50
INDEX_HINTS = ("指数", "上证", "深证", "沪深", "中证", "创业板", "科创", "北证", "全指")
_PATH = Path(__file__).with_name("stock_directory.csv")
_cache: list[Stock] | None = None


def _load() -> list[Stock] | None:
    global _cache
    if _cache is not None:
        return _cache
    if not _PATH.exists():
        return None
    stocks: list[Stock] = []
    try:
        with _PATH.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                stocks.append(
                    Stock(
                        code=row["code"],
                        name=row["name"],
                        is_index=row["is_index"] == "1",
                    )
                )
    except (OSError, KeyError, ValueError):
        return None
    _cache = stocks
    return stocks


def available() -> bool:
    return _load() is not None


def search(keyword: str) -> list[Stock] | None:
    """返回本地匹配结果；目录不可用时返回 None，让数据源回退到在线搜索。"""
    stocks = _load()
    if stocks is None:
        return None
    keyword = keyword.strip().lower()
    if not keyword:
        return []
    digits = keyword.replace(".", "")
    full_code = digits.isdigit() and len(digits) == 6
    include_indices = full_code or any(hint in keyword for hint in INDEX_HINTS)
    exact: list[Stock] = []
    partial: list[Stock] = []
    for stock in stocks:
        if stock.is_index and not include_indices:
            continue
        code = stock.code.lower()
        name = stock.name.lower()
        if full_code and (code == keyword or code.endswith("." + digits)):
            exact.append(stock)
        elif name == keyword:
            exact.append(stock)
        elif keyword in name or (not full_code and keyword in code and not digits.isdigit()):
            partial.append(stock)
    return (exact + partial)[:MAX_RESULTS]
