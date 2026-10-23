"""行情数据模型。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


class DataError(RuntimeError):
    """行情查询失败。"""


@dataclass(frozen=True)
class Stock:
    code: str
    name: str
    is_index: bool = False


@dataclass(frozen=True)
class Bars:
    code: str
    freq: str
    adjust: str
    is_index: bool
    dates: np.ndarray
    open: np.ndarray
    high: np.ndarray
    low: np.ndarray
    close: np.ndarray
    preclose: np.ndarray
    volume: np.ndarray
    amount: np.ndarray
    turn: np.ndarray
    pct_chg: np.ndarray
    full: bool = False

    def __len__(self) -> int:
        return len(self.dates)
