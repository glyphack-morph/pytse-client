"""Live tests of pytse_client.tsetmc_api.index (they call the TSETMC
API)."""

import unittest

from pytse_client.tsetmc_api import index

from .typecheck import FOLAD, TOTAL_INDEX, assert_field_types


class TestIndexHistory(unittest.TestCase):
    def test_index_history(self):
        # TSE_FINANCIAL_INDEX_EXPORT_DATA_ADDRESS
        days = index.fetch_index_history(TOTAL_INDEX)
        self.assertGreater(len(days), 1000)
        assert_field_types(self, days)
        self.assertGreaterEqual(days[-1].high, days[-1].low)


class TestIndexIntraday(unittest.TestCase):
    def test_index_intraday(self):
        # FINANCIAL_INDEX_EXPORT_INTRADAY_URL
        rows = index.fetch_index_intraday(TOTAL_INDEX)
        self.assertGreater(len(rows), 0)
        assert_field_types(self, rows)
        self.assertGreater(max(row.value for row in rows), 0)


class TestIndices(unittest.TestCase):
    def test_indices(self):
        # INDICES_LIST_URL, flow 1 بورس and 2 فرابورس
        for flow in [1, 2]:
            rows = index.fetch_indices(flow)
            self.assertGreater(len(rows), 5)
            assert_field_types(self, rows)
        rows = index.fetch_indices(1)
        self.assertIn(TOTAL_INDEX, {row.ins_code for row in rows})


class TestIndexCompanies(unittest.TestCase):
    def test_index_companies(self):
        # FINANCIAL_INDEX_COMPANIES_URL
        companies = index.fetch_index_companies(TOTAL_INDEX)
        self.assertGreater(len(companies.companies), 100)
        assert_field_types(self, companies)
        [folad] = [c for c in companies.companies if c.ins_code == FOLAD]
        self.assertEqual(folad.instrument.symbol, "فولاد")


if __name__ == "__main__":
    unittest.main()
