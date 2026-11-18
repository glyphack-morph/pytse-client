"""Live tests of pytse_client.tsetmc_api.shareholder (they call the
TSETMC API)."""

import unittest

from pytse_client.tsetmc_api import shareholder

from .typecheck import FOLAD, HISTORY_DAY, assert_field_types


class TestShareholders(unittest.TestCase):
    def test_shareholders(self):
        # TSE_SHAREHOLDERS_URL
        rows = shareholder.fetch_shareholders(FOLAD)
        self.assertGreater(len(rows), 0)
        assert_field_types(self, rows)
        self.assertLessEqual(sum(row.percentage for row in rows), 100)


class TestDayShareholders(unittest.TestCase):
    def test_day_shareholders(self):
        # SYMBOL_DAY_INFO_SHAREHOLDERS_DATA
        rows = shareholder.fetch_day_shareholders(FOLAD, HISTORY_DAY)
        self.assertGreater(len(rows), 0)
        assert_field_types(self, rows)
        self.assertIn(HISTORY_DAY, {row.date for row in rows})


if __name__ == "__main__":
    unittest.main()
