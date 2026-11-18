"""Live tests of pytse_client.tsetmc_api.market (they call the TSETMC
API)."""

import datetime
import unittest

from pytse_client.tsetmc_api import market

from .typecheck import FOLAD, assert_field_types


class TestMarketOverview(unittest.TestCase):
    def test_market_overview(self):
        # TSE_GET_LAST_TRADE_DAY
        overview = market.fetch_market_overview()
        assert_field_types(self, overview)
        self.assertLessEqual(overview.last_trade_date, datetime.date.today())
        self.assertGreater(
            overview.last_trade_date,
            datetime.date.today() - datetime.timedelta(30),
        )


class TestMarketWatch(unittest.TestCase):
    def test_market_watch(self):
        # MARKET_WATCH_URL
        rows = market.fetch_market_watch()
        self.assertGreater(len(rows), 1000)
        assert_field_types(self, rows)
        [folad] = [row for row in rows if row.ins_code == FOLAD]
        self.assertEqual(folad.symbol, "فولاد")
        self.assertEqual(folad.isin, "IRO1FOLD0001")
        self.assertEqual(folad.flow, 1)
        self.assertGreater(folad.total_shares, 0)
        self.assertEqual(
            [level.level for level in folad.best_limits], [1, 2, 3, 4, 5]
        )


class TestKeyStats(unittest.TestCase):
    def test_key_stats(self):
        # KEY_STATS_URL
        rows = market.fetch_key_stats()
        self.assertGreater(len(rows), 100000)
        assert_field_types(self, rows)
        folad = {
            row.stat_id: row.value for row in rows if row.ins_code == FOLAD
        }
        # 1: ave_val_trans_last_3_month, see ticker_statisticals/key_stats.py
        self.assertGreater(folad[1], 0)


if __name__ == "__main__":
    unittest.main()
