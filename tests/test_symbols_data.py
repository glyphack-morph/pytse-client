import json
import shutil
import unittest
from dataclasses import astuple
from os.path import exists
from pathlib import Path

from pytse_client import symbols_data
from pytse_client.scraper.symbol_scraper import (
    MarketSymbol,
    load_market_symbols_from_json,
)
from pytse_client.scripts.update_symbols_json import write_symbols_to_json


class TestSymbolsData(unittest.TestCase):
    def setUp(self) -> None:
        self.write_path = "test_symbol_data_dir"
        return super().setUp()

    def tearDown(self) -> None:
        if exists(self.write_path):
            shutil.rmtree(self.write_path)
        return super().tearDown()

    def test_update_symbols_json_file(self):
        market_symbols = [
            MarketSymbol(
                code="IRO1NBAB0001",
                symbol="آبادا",
                name="تولید نیروی برق آبادان",
                index="37661500521100963",
                old=["18621338450655320"],
            ),
            MarketSymbol(
                code="IRO1FOLD0001",
                symbol="فولاد",
                name="فولاد مبارکه اصفهان",
                index="46348559193224090",
                old=[],
            ),
        ]
        write_symbols_to_json(
            market_symbols, "symbols_name.json", self.write_path
        )
        path = Path(f"{self.write_path}/symbols_name.json")
        self.assertTrue(exists(path))
        with open(path, encoding="utf8") as file:
            data = json.load(file)
        self.assertEqual(
            data["آبادا"],
            {
                "index": "37661500521100963",
                "code": "IRO1NBAB0001",
                "name": "تولید نیروی برق آبادان",
                "old": ["18621338450655320"],
            },
        )
        # MarketSymbol.__eq__ only compares the symbol, compare every field
        self.assertEqual(
            [astuple(s) for s in load_market_symbols_from_json(path)],
            [astuple(s) for s in market_symbols],
        )

    def test_get_ticker_index(self) -> None:
        symbol = "وبملت"
        expected_index = "778253364357513"
        self.assertEqual(symbols_data.get_ticker_index(symbol), expected_index)

    def test_bundled_symbols_json(self) -> None:
        info = symbols_data.symbols_information()
        self.assertGreater(len(info), 1000)
        self.assertEqual(info["فولاد"]["index"], "46348559193224090")
        self.assertEqual(info["فولاد"]["code"], "IRO1FOLD0001")
        self.assertIn(
            "18621338450655320", symbols_data.get_ticker_old_index("آبادا")
        )
        for symbol, value in info.items():
            self.assertEqual(set(value), {"index", "code", "name", "old"})
        # deleted symbols are kept, their index is in their old list
        self.assertIn(info["شوش"]["index"], info["شوش"]["old"])
        self.assertNotIn(info["فولاد"]["index"], info["فولاد"]["old"])

    def test_old_indexes_are_not_active_under_another_symbol(self) -> None:
        # an index in a symbol's old list is read as part of that symbol's
        # history, and Ticker(index=...) treats it as inactive. A renamed
        # instrument keeps its index under the new symbol (e.g. the fund
        # once named سحرخیز is now سافرون), so that index must not stay in
        # the old list of the previous symbol.
        info = symbols_data.symbols_information()
        active = {
            value["index"]: symbol
            for symbol, value in info.items()
            if value["index"] not in value["old"]
        }
        conflicts = [
            (symbol, old, active[old])
            for symbol, value in info.items()
            for old in value["old"]
            if old in active and active[old] != symbol
        ]
        self.assertEqual(conflicts, [])

    def test_bundled_indices_json(self) -> None:
        self.assertEqual(
            symbols_data.get_financial_index("شاخص كل"), "32097828799138957"
        )
        self.assertEqual(
            symbols_data.get_financial_index("شاخص كل فرابورس"),
            "43685683301327984",
        )


if __name__ == "__main__":
    unittest.main()
