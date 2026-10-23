"""经典技术指标计算：纯 numpy，不依赖界面。"""

from __future__ import annotations

import numpy as np


def sma(values: np.ndarray, period: int) -> np.ndarray:
    data = np.asarray(values, dtype=float)
    result = np.full(data.shape, np.nan, dtype=float)
    if period <= 0 or data.size < period:
        return result
    windows = np.lib.stride_tricks.sliding_window_view(data, period)
    valid = np.isfinite(windows)
    counts = valid.sum(axis=1)
    sums = np.where(valid, windows, 0.0).sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        values = sums / counts
    values[counts == 0] = np.nan
    result[period - 1 :] = values
    return result


def ema(values: np.ndarray, period: int) -> np.ndarray:
    if period <= 0:
        raise ValueError("EMA 周期必须为正")
    data = np.asarray(values, dtype=float)
    result = np.empty(data.shape, dtype=float)
    if data.size == 0:
        return result
    result[0] = data[0]
    alpha = 2.0 / (period + 1)
    for index in range(1, data.size):
        result[index] = alpha * data[index] + (1 - alpha) * result[index - 1]
    return result


def macd(
    close: np.ndarray,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """返回 DIF、DEA 与 MACD 柱；柱按国内软件惯例取 2*(DIF-DEA)。"""
    dif = ema(close, fast) - ema(close, slow)
    dea = ema(dif, signal)
    return dif, dea, (dif - dea) * 2.0


def boll(
    close: np.ndarray,
    period: int = 20,
    width: float = 2.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """布林带：中轨为 SMA，上下轨为中轨 ± width 倍总体标准差。"""
    data = np.asarray(close, dtype=float)
    mid = sma(data, period)
    upper = np.full(data.shape, np.nan, dtype=float)
    lower = np.full(data.shape, np.nan, dtype=float)
    if period > 0 and data.size >= period:
        windows = np.lib.stride_tricks.sliding_window_view(data, period)
        std = windows.std(axis=1)
        upper[period - 1 :] = mid[period - 1 :] + width * std
        lower[period - 1 :] = mid[period - 1 :] - width * std
    return mid, upper, lower


def kdj(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    period: int = 9,
    k_smooth: int = 3,
    d_smooth: int = 3,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if period <= 0 or k_smooth <= 0 or d_smooth <= 0:
        raise ValueError("KDJ 参数必须为正")
    high = np.asarray(high, dtype=float)
    low = np.asarray(low, dtype=float)
    close = np.asarray(close, dtype=float)
    size = close.size
    k = np.empty(size, dtype=float)
    d = np.empty(size, dtype=float)
    j = np.empty(size, dtype=float)
    previous_k = 50.0
    previous_d = 50.0
    for index in range(size):
        start = max(0, index - period + 1)
        highest = float(np.max(high[start : index + 1]))
        lowest = float(np.min(low[start : index + 1]))
        if highest <= lowest:
            rsv = 50.0
        else:
            rsv = (close[index] - lowest) / (highest - lowest) * 100.0
        previous_k = (
            (k_smooth - 1) * previous_k + rsv
        ) / k_smooth
        previous_d = (
            (d_smooth - 1) * previous_d + previous_k
        ) / d_smooth
        k[index] = previous_k
        d[index] = previous_d
        j[index] = 3.0 * previous_k - 2.0 * previous_d
    return k, d, j


def _rsi_value(gain: float, loss: float) -> float:
    if loss <= 0:
        return 50.0 if gain <= 0 else 100.0
    return 100.0 - 100.0 / (1.0 + gain / loss)


def rsi(close: np.ndarray, period: int = 14) -> np.ndarray:
    """Wilder RSI：首值取前 period 根的平均涨跌，之后用平滑平均。"""
    if period <= 0:
        raise ValueError("RSI 周期必须为正")
    data = np.asarray(close, dtype=float)
    result = np.full(data.shape, np.nan, dtype=float)
    if data.size <= period:
        return result
    delta = np.diff(data)
    gains = np.maximum(delta, 0.0)
    losses = np.maximum(-delta, 0.0)
    average_gain = float(gains[:period].mean())
    average_loss = float(losses[:period].mean())
    result[period] = _rsi_value(average_gain, average_loss)
    for index in range(period + 1, data.size):
        average_gain = (average_gain * (period - 1) + gains[index - 1]) / period
        average_loss = (average_loss * (period - 1) + losses[index - 1]) / period
        result[index] = _rsi_value(average_gain, average_loss)
    return result
