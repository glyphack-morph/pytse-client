import shutil
import unittest
from os.path import exists
from pathlib import Path

import pandas as pd
from pytse_client import (
    download,
    download_client_types_records,
    download_financial_indexes,
)
from pytse_client.download import get_symbol_id


class TestDownloadSymbolHistory(unittest.TestCase):
    def setUp(self) -> None:
        self.valid_symbols = ["وبملت", "ذوب"]
        self.valid_symbol = "فولاد"
        self.write_csv_path = "test_symbol_records_dir"
        return super().setUp()

    def tearDown(self) -> None:
        shutil.rmtree(self.write_csv_path)
        return super().tearDown()

    def test_download_a_single_symbol_history(self):
        symbol_record = download(
            symbols=self.valid_symbol,
            write_to_csv=True,
            base_path=self.write_csv_path,
        )[self.valid_symbol]
        self.assertTrue(
            exists(Path(f"{self.write_csv_path}/{self.valid_symbol}.csv"))
        )
        self.assertFalse(symbol_record.empty)
        # api: ClosingPrice/GetClosingPriceDailyList
        self.assertEqual(
            list(symbol_record.columns),
            [
                "date",
                "open",
                "high",
                "low",
                "adjClose",
                "value",
                "volume",
                "count",
                "yesterday",
                "close",
            ],
        )
        self.assertTrue(symbol_record["date"].is_monotonic_increasing)
        # the whole history is downloaded, فولاد was listed in 2007
        self.assertLess(
            symbol_record["date"].iloc[0], pd.Timestamp("2008-01-01")
        )

    def test_download_multiple_symbols(self):
        symbols_records = download(
            symbols=self.valid_symbols,
            write_to_csv=True,
            base_path=self.write_csv_path,
        )
        for symbol, symbol_record in symbols_records.items():
            self.assertTrue(
                exists(Path(f"{self.write_csv_path}/{symbol}.csv"))
            )
            self.assertFalse(symbol_record.empty)


class TestDownloadClientTypes(unittest.TestCase):
    def setUp(self) -> None:
        self.valid_symbols = ["وبملت", "ذوب"]
        self.valid_symbol = "فولاد"
        self.write_csv_path = "test_client_type_data_dir"
        return super().setUp()

    def tearDown(self) -> None:
        shutil.rmtree(self.write_csv_path)
        return super().tearDown()

    def test_download_a_single_symbol_client_types_records(self):
        symbol_record = download_client_types_records(
            symbols=self.valid_symbol,
            write_to_csv=True,
            base_path=self.write_csv_path,
        )[self.valid_symbol]
        self.assertTrue(
            exists(Path(f"{self.write_csv_path}/{self.valid_symbol}.csv"))
        )
        self.assertFalse(symbol_record.empty)

    def test_download_multiple_symbols_client_types_records(self):
        symbols_records = download_client_types_records(
            symbols=self.valid_symbols,
            write_to_csv=True,
            base_path=self.write_csv_path,
        )
        for symbol, symbol_record in symbols_records.items():
            self.assertTrue(
                exists(Path(f"{self.write_csv_path}/{symbol}.csv"))
            )
            self.assertFalse(symbol_record.empty)


class TestDownloadAdjustedHistory(unittest.TestCase):
    def test_download_adjusted_history(self):
        symbol = "فولاد"
        adjusted = download(symbols=symbol, adjust=True)[symbol]
        not_adjusted = download(symbols=symbol)[symbol]
        self.assertEqual(len(adjusted), len(not_adjusted))
        # the last day is never changed by the adjustment
        self.assertEqual(
            adjusted["adjClose"].iloc[-1], not_adjusted["adjClose"].iloc[-1]
        )
        # فولاد had capital increases, so old prices are adjusted
        self.assertLess(
            adjusted["adjClose"].iloc[0], not_adjusted["adjClose"].iloc[0]
        )


class TestDownloadFinancialIndex(unittest.TestCase):
    def test_download_financial_index(self):
        # api: Index/GetIndexB2History
        [records] = download_financial_indexes(
            "شاخص کل", include_jdate=True
        ).values()
        self.assertEqual(
            list(records.columns), ["date", "high", "low", "close", "jdate"]
        )
        self.assertGreater(len(records), 1000)
        self.assertTrue(records["date"].is_monotonic_increasing)


class TestGetSymbolId(unittest.TestCase):
    def test_get_symbol_id(self):
        # api: Instrument/GetInstrumentSearch
        self.assertEqual(get_symbol_id("فولاد"), "46348559193224090")


def suite():
    suite = unittest.TestSuite()
    suite.addTest(TestDownloadSymbolHistory("test_download_symbol_history"))
    suite.addTest(TestDownloadClientTypes("test_download_client_types"))
    return suite


if __name__ == "__main__":
    runner = unittest.TextTestRunner()
    runner.run(suite())
