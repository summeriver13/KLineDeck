"""技术指标计算的回归测试。"""

from __future__ import annotations

import unittest

import numpy as np

from candleline.indicators import boll, ema, kdj, macd, rsi, sma


class SmaTest(unittest.TestCase):
    def test_window_mean(self) -> None:
        result = sma(np.arange(1, 7, dtype=float), 3)
        np.testing.assert_allclose(
            result[2:], [2.0, 3.0, 4.0, 5.0], equal_nan=True
        )
        self.assertTrue(np.isnan(result[:2]).all())

    def test_ignores_missing_values(self) -> None:
        result = sma(np.array([1.0, np.nan, 3.0, 5.0]), 3)
        np.testing.assert_allclose(result[2:], [2.0, 4.0], equal_nan=True)


class EmaTest(unittest.TestCase):
    def test_recursive_formula(self) -> None:
        result = ema(np.array([1.0, 2.0, 3.0, 4.0]), 3)
        np.testing.assert_allclose(result, [1.0, 1.5, 2.25, 3.125])


class MacdTest(unittest.TestCase):
    def test_components_and_histogram(self) -> None:
        close = np.linspace(10.0, 20.0, 120)
        dif, dea, histogram = macd(close)
        np.testing.assert_allclose(dif, ema(close, 12) - ema(close, 26))
        np.testing.assert_allclose(dea, ema(dif, 9))
        np.testing.assert_allclose(histogram, (dif - dea) * 2.0)


class BollTest(unittest.TestCase):
    def test_constant_series_is_flat(self) -> None:
        mid, upper, lower = boll(np.full(30, 10.0))
        np.testing.assert_allclose(mid[19:], 10.0)
        np.testing.assert_allclose(upper[19:], 10.0)
        np.testing.assert_allclose(lower[19:], 10.0)

    def test_band_matches_sample(self) -> None:
        close = np.arange(1.0, 31.0)
        mid, upper, lower = boll(close, period=20, width=2.0)
        window = close[-20:]
        np.testing.assert_allclose(mid[-1], window.mean())
        np.testing.assert_allclose(upper[-1], window.mean() + 2.0 * window.std())
        np.testing.assert_allclose(lower[-1], window.mean() - 2.0 * window.std())


class KdjTest(unittest.TestCase):
    def test_constant_series_stays_neutral(self) -> None:
        k, d, j = kdj(
            np.full(30, 11.0), np.full(30, 9.0), np.full(30, 10.0)
        )
        np.testing.assert_allclose(k, 50.0)
        np.testing.assert_allclose(d, 50.0)
        np.testing.assert_allclose(j, 50.0)

    def test_rising_series_and_j_identity(self) -> None:
        close = np.arange(1.0, 31.0)
        high = close + 1.0
        low = close - 1.0
        k, d, j = kdj(high, low, close)
        np.testing.assert_allclose(j, 3.0 * k - 2.0 * d)
        self.assertGreater(k[-1], 50.0)
        self.assertLessEqual(k[-1], 100.0)
        self.assertGreaterEqual(d[-1], 0.0)


class RsiTest(unittest.TestCase):
    def test_warmup_is_nan(self) -> None:
        result = rsi(np.arange(1.0, 20.0), 14)
        self.assertTrue(np.isnan(result[:14]).all())
        self.assertTrue(np.isfinite(result[14:]).all())

    def test_monotonic_series_extremes(self) -> None:
        increasing = rsi(np.arange(1.0, 31.0), 14)
        decreasing = rsi(np.arange(30.0, 0.0, -1.0), 14)
        flat = rsi(np.full(30, 10.0), 14)
        self.assertEqual(increasing[-1], 100.0)
        self.assertEqual(decreasing[-1], 0.0)
        self.assertEqual(flat[-1], 50.0)


if __name__ == "__main__":
    unittest.main()
