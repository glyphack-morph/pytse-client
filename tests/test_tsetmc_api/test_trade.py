"""Live tests of pytse_client.tsetmc_api.trade (they call the TSETMC
API)."""

import unittest

from pytse_client.tsetmc_api import trade

from .typecheck import FOLAD, HISTORY_DAY, assert_field_types


class TestTrades(unittest.TestCase):
    def test_trades(self):
        # TSE_TRADE_DETAIL_URL
        trades = trade.fetch_trades(FOLAD)
        self.assertGreater(len(trades), 100)
        assert_field_types(self, trades)


class TestTradeHistory(unittest.TestCase):
    def test_trade_history(self):
        # TICKER_TRADE_DETAILS
        trades = trade.fetch_trade_history(FOLAD, HISTORY_DAY)
        self.assertGreater(len(trades), 1000)
        assert_field_types(self, trades)
        unique = trade.unique_trades(trades)
        self.assertEqual(
            len(unique), len({t.number for t in trades if not t.canceled})
        )
        self.assertFalse(any(t.canceled for t in unique))


if __name__ == "__main__":
    unittest.main()
