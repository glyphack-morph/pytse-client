"""Live tests of pytse_client.tsetmc_api.best_limits (they call the TSETMC
API)."""

import unittest

from pytse_client.tsetmc_api import best_limits

from .typecheck import FOLAD, HISTORY_DAY, assert_field_types


class TestBestLimits(unittest.TestCase):
    def test_best_limits(self):
        # TSE_BEST_LIMITS_URL
        rows = best_limits.fetch_best_limits(FOLAD)
        self.assertEqual(sorted(row.level for row in rows), [1, 2, 3, 4, 5])
        assert_field_types(self, rows)
        buy_orders, sell_orders = best_limits.orders_from_best_limits(rows)
        self.assertEqual(len(buy_orders), 5)
        self.assertIsInstance(sell_orders[0], best_limits.Order)


class TestBestLimitsHistory(unittest.TestCase):
    def test_best_limits_history(self):
        # TICKER_ORDER_BOOK
        rows = best_limits.fetch_best_limits_history(FOLAD, HISTORY_DAY)
        self.assertGreater(len(rows), 1000)
        assert_field_types(self, rows)
        self.assertEqual({row.level for row in rows}, {1, 2, 3, 4, 5})


if __name__ == "__main__":
    unittest.main()
