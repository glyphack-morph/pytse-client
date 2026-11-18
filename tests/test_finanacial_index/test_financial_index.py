import shutil
import unittest
from os.path import exists
from pathlib import Path

from pytse_client import FinancialIndex


class TestFinancialIndex(unittest.TestCase):
    def setUp(self) -> None:
        self.valid_f_index = "شاخص قيمت 50 شركت"
        self.write_csv_path = "test_financial_index_dir"
        return super().setUp()

    def tearDown(self) -> None:
        if exists(self.write_csv_path):
            shutil.rmtree(self.write_csv_path)
        return super().tearDown()

    def test_download_history(self):
        f_index_record = FinancialIndex(
            self.valid_f_index,
            base_path=self.write_csv_path,
            write_history=True,
        ).history
        self.assertTrue(
            exists(Path(f"{self.write_csv_path}/{self.valid_f_index}.csv"))
        )
        self.assertFalse(f_index_record.empty)
        # api: Index/GetIndexB2History, it has no open and volume
        expected_columns = [
            "jdate",
            "date",
            "close",
            "high",
            "low",
        ]
        missing_columns = [
            col
            for col in expected_columns
            if col not in f_index_record.columns
        ]
        self.assertEqual(
            len(missing_columns), 0, f"Missing columns: {missing_columns}"
        )

    def test_fields(self):
        f_index_record = FinancialIndex(
            self.valid_f_index,
        )
        self.assertTrue(
            f_index_record.low
            and f_index_record.high
            and f_index_record.last_update
            and f_index_record.last_value
            and f_index_record.contributing_symbols
            and len(f_index_record.intraday_price)
        )

    def test_last_values(self):
        # api: Index/GetIndexB1LastDay
        f_index = FinancialIndex(self.valid_f_index)
        self.assertRegex(f_index.last_update, r"^\d\d:\d\d$")
        self.assertGreater(f_index.last_value, 0)
        self.assertGreaterEqual(f_index.high, f_index.low)
        self.assertGreater(f_index.low, 0)

    def test_intraday_price(self):
        # api: Index/GetIndexB1LastDay
        intraday = FinancialIndex(self.valid_f_index).intraday_price
        self.assertEqual(
            list(intraday.columns),
            ["value", "change_percentage", "low", "high"],
        )
        self.assertFalse(intraday.empty)
        self.assertTrue(intraday.index.is_monotonic_increasing)

    def test_contributing_symbols(self):
        # api: ClosingPrice/GetIndexCompany
        symbols = FinancialIndex("شاخص کل").contributing_symbols
        self.assertGreater(len(symbols), 100)
        self.assertIn(
            {"symbol": "فولاد", "index": "46348559193224090"}, symbols
        )


if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestFinancialIndex)
    unittest.TextTestRunner(verbosity=3).run(suite)
