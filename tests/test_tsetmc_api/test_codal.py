"""Live tests of pytse_client.tsetmc_api.codal (they call the TSETMC
API)."""

import unittest

from pytse_client.tsetmc_api import codal

from .typecheck import assert_field_types


class TestCodalPublisher(unittest.TestCase):
    def test_codal_publisher(self):
        # TSE_TICKER_INTRODUCTION_URL, takes the symbol
        publisher = codal.fetch_codal_publisher("فولاد")
        assert_field_types(self, publisher)
        self.assertEqual(publisher.financial_year, "12/29")
        self.assertGreater(publisher.listed_capital, 0)


if __name__ == "__main__":
    unittest.main()
