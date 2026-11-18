"""Live tests of pytse_client.tsetmc_api.fund (they call the TSETMC
API)."""

import unittest

from pytse_client.tsetmc_api import fund

from .typecheck import FUND, assert_field_types


class TestEtf(unittest.TestCase):
    def test_etf(self):
        # TSE_ETF_URL, for the fund كاريس
        etf = fund.fetch_etf(FUND)
        assert_field_types(self, etf)
        self.assertGreater(etf.redemption_nav, 0)
        self.assertGreater(etf.subscription_nav, 0)


if __name__ == "__main__":
    unittest.main()
