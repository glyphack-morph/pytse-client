"""Live tests of pytse_client.tsetmc_api.client_type (they call the TSETMC
API)."""

import unittest

from pytse_client.tsetmc_api import client_type

from .typecheck import FOLAD, assert_field_types


class TestClientType(unittest.TestCase):
    def test_client_type(self):
        # TSE_CLIENT_TYPE_URL
        totals = client_type.fetch_client_type(FOLAD)
        assert_field_types(self, totals)
        self.assertEqual(
            totals.individual_buy_volume + totals.corporate_buy_volume,
            totals.individual_sell_volume + totals.corporate_sell_volume,
        )
        summary = client_type.individual_trade_summary(totals)
        self.assertIsInstance(summary, client_type.TradeSummary)
        self.assertIsInstance(summary.buy_vol, float)


class TestClientTypeAll(unittest.TestCase):
    def test_client_type_all(self):
        # CLIENT_TYPES_URL
        rows = client_type.fetch_client_type_all()
        self.assertGreater(len(rows), 500)
        assert_field_types(self, rows)
        for row in rows:
            self.assertIsInstance(row.ins_code, str)
        self.assertIn(FOLAD, {row.ins_code for row in rows})


class TestClientTypeHistory(unittest.TestCase):
    def test_client_type_history(self):
        # TSE_CLIENT_TYPE_DATA_URL
        days = client_type.fetch_client_type_history(FOLAD)
        self.assertGreater(len(days), 1000)
        assert_field_types(self, days)
        # newest day first
        self.assertGreater(days[0].date, days[-1].date)


if __name__ == "__main__":
    unittest.main()
