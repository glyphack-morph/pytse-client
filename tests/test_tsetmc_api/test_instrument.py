"""Live tests of pytse_client.tsetmc_api.instrument (they call the TSETMC
API)."""

import unittest

from pytse_client.tsetmc_api import instrument

from .typecheck import (
    FOLAD,
    FUND,
    HISTORY_DAY,
    TOTAL_INDEX,
    assert_field_types,
)


class TestInstrumentInfo(unittest.TestCase):
    def test_instrument_info(self):
        # TSE_INSTRUMENT_INFO
        info = instrument.fetch_instrument_info(FOLAD)
        assert_field_types(self, info)
        self.assertEqual(info.symbol, "فولاد")
        self.assertEqual(info.isin, "IRO1FOLD0001")
        self.assertEqual(info.company_isin, "IRO1FOLD0009")
        self.assertIsInstance(info.eps.estimated_eps, float)
        self.assertGreater(
            info.static_threshold.max_price, info.static_threshold.min_price
        )

    def test_instrument_info_of_index_and_fund(self):
        for ins_code in [TOTAL_INDEX, FUND]:
            info = instrument.fetch_instrument_info(ins_code)
            assert_field_types(self, info)
            self.assertIsNone(info.eps.estimated_eps)


class TestInstrumentSearch(unittest.TestCase):
    def test_instrument_search(self):
        # TSE_SYMBOL_ID_URL
        results = instrument.fetch_instrument_search("فولاد")
        self.assertGreater(len(results), 1)
        assert_field_types(self, results)
        [folad] = [row for row in results if row.ins_code == FOLAD]
        self.assertEqual(folad.symbol, "فولاد")
        self.assertFalse(folad.is_deleted)


class TestInstrumentHistory(unittest.TestCase):
    def test_instrument_history(self):
        # SYMBOL_DAY_INSTRUMENT_INFO_URL
        history = instrument.fetch_instrument_history(FOLAD, HISTORY_DAY)
        assert_field_types(self, history)
        self.assertGreater(history.total_shares, 0)
        self.assertEqual(history.symbol, "فولاد")


if __name__ == "__main__":
    unittest.main()
