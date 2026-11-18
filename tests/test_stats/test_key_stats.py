import shutil
import unittest
from os.path import exists
from pathlib import Path

from pytse_client import get_stats


class TestKeyStats(unittest.TestCase):
    def setUp(self) -> None:
        self.write_csv_path = "test_key_stats_dir"
        return super().setUp()

    def tearDown(self) -> None:
        shutil.rmtree(self.write_csv_path)
        return super().tearDown()

    def test_key_stats(self):
        df = get_stats(base_path=self.write_csv_path, to_csv=True)
        self.assertTrue(exists(Path(f"{self.write_csv_path}/key_stats.csv")))
        self.assertFalse(df.empty)
        # apis: MarketData/GetInstValueAllInstAllParam,
        # ClientType/GetClientTypeAll, ClosingPrice/GetMarketWatch
        row = df[df["symbol"] == "فولاد"].iloc[0]
        self.assertEqual(row["index"], "46348559193224090")
        self.assertGreater(row["ave_val_trans_last_3_month"], 0)
        self.assertGreaterEqual(row["numof_individual_buy"], 0)
        self.assertGreater(row["last_price"], 0)
        self.assertGreater(row["number_of_stocks"], 0)


if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestKeyStats)
    unittest.TextTestRunner(verbosity=3).run(suite)
