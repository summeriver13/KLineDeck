"""历史数据向前补充与缓存合并的回归测试。"""

from __future__ import annotations

import os
import tempfile
import unittest
from dataclasses import replace
from datetime import date, timedelta

import numpy as np

from candleline import cache, data, stock_directory
from candleline.models import Bars, DataError, Stock


class FakeSource:
    name = "fake"

    def __init__(self) -> None:
        self.calls: list[tuple[str, str | None]] = []

    def full_start(self, freq: str) -> str:
        return "2020-01-01"

    def search(self, keyword: str) -> list[Stock]:
        return []

    def fetch(
        self,
        code: str,
        freq: str,
        adjust: str,
        is_index: bool,
        start: str,
        end: str | None = None,
    ) -> Bars:
        self.calls.append((start, end))
        first = date.fromisoformat(start)
        last = date.fromisoformat(end or "2023-12-29")
        days: list[date] = []
        current = first
        while current <= last:
            if current.weekday() < 5:
                days.append(current)
            current += timedelta(days=1)
        if not days:
            raise DataError("没有数据")
        dates = np.array(days, dtype="datetime64[D]")
        count = len(dates)
        close = np.arange(count, dtype=float) + 10.0
        return Bars(
            code=code,
            freq=freq,
            adjust=adjust,
            is_index=is_index,
            dates=dates,
            open=close,
            high=close + 1.0,
            low=close - 1.0,
            close=close,
            preclose=close,
            volume=np.ones(count),
            amount=np.ones(count),
            turn=np.ones(count),
            pct_chg=np.zeros(count),
        )


class FetchOlderTest(unittest.TestCase):
    def setUp(self) -> None:
        self.source = FakeSource()
        self.old_source = data._source
        data.set_source(self.source)
        self.temp_dir = tempfile.TemporaryDirectory()
        self.old_cache_dir = os.environ.get("CANDLELINE_CACHE_DIR")
        os.environ["CANDLELINE_CACHE_DIR"] = self.temp_dir.name

    def tearDown(self) -> None:
        data.set_source(self.old_source)
        if self.old_cache_dir is None:
            os.environ.pop("CANDLELINE_CACHE_DIR", None)
        else:
            os.environ["CANDLELINE_CACHE_DIR"] = self.old_cache_dir
        self.temp_dir.cleanup()

    def current(self, start: str) -> Bars:
        return self.source.fetch(
            "sh.600000", "d", "qfq", False, start, "2023-12-29"
        )

    def test_prepends_older_rows_without_duplicates(self) -> None:
        current = self.current("2023-01-02")
        result = data.fetch_older(current)

        self.assertGreater(len(result), len(current))
        self.assertEqual(result.dates[0], np.datetime64("2021-01-04"))
        self.assertEqual(len(result.dates), len(np.unique(result.dates)))
        self.assertFalse(result.full)
        cached = cache.load("fake", "sh.600000", "d", "qfq")
        self.assertIsNotNone(cached)
        self.assertEqual(len(cached[0]), len(result))

    def test_marks_complete_when_full_start_is_reached(self) -> None:
        current = self.current("2021-01-04")
        result = data.fetch_older(current)

        self.assertTrue(result.full)
        self.assertEqual(result.dates[0], np.datetime64("2020-01-01"))

    def test_returns_current_when_already_complete(self) -> None:
        current = replace(self.current("2023-01-02"), full=True)
        calls = len(self.source.calls)
        result = data.fetch_older(current)

        self.assertIs(result, current)
        self.assertEqual(len(self.source.calls), calls)


class StockDirectoryTest(unittest.TestCase):
    def test_name_and_code_search_are_local(self) -> None:
        self.assertTrue(stock_directory.available())

        self.assertEqual(stock_directory.search("腾讯"), [])
        codes = [stock.code for stock in stock_directory.search("600000")]
        self.assertEqual(codes, ["sh.600000"])

        names = [stock.code for stock in stock_directory.search("浦发")]
        self.assertIn("sh.600000", names)

        indices = stock_directory.search("上证")
        self.assertIsNotNone(indices)
        self.assertIn("sh.000001", [stock.code for stock in indices])


if __name__ == "__main__":
    unittest.main()
