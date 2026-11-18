"""Live tests of pytse_client.tsetmc_api.closing_price (they call the
TSETMC API)."""

import unittest

from pytse_client.tsetmc_api import closing_price

from .typecheck import FOLAD, FUND, assert_field_types


class TestClosingPriceInfo(unittest.TestCase):
    def test_closing_price_info(self):
        # TSE_CLOSING_PRICE_INFO_URL
        for ins_code in [FOLAD, FUND]:
            info = closing_price.fetch_closing_price_info(ins_code)
            assert_field_types(self, info)
            self.assertIsNotNone(info.instrument_state)
            self.assertGreater(info.closing_price, 0)
            self.assertGreaterEqual(info.high_price, info.low_price)


class TestClosingPriceDailyList(unittest.TestCase):
    def test_closing_price_daily_list(self):
        # TSE_TICKER_EXPORT_DATA_ADDRESS
        days = closing_price.fetch_closing_price_daily_list(FOLAD)
        self.assertGreater(len(days), 1000)
        assert_field_types(self, days)
        # newest day first
        self.assertGreater(days[0].date, days[-1].date)


class TestClosingPriceDailyAllInst(unittest.TestCase):
    def test_closing_price_daily_all_inst(self):
        # CLOSING_PRICE_DAILY_ALL_INST_URL, about 55 MB
        rows = closing_price.fetch_closing_price_daily_all_inst()
        self.assertGreater(len(rows), 10000)
        assert_field_types(self, rows)
        self.assertIn(FOLAD, {row.ins_code for row in rows})


if __name__ == "__main__":
    unittest.main()
