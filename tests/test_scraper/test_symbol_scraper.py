"""Tests of the symbols and indices scrapers.

The tests whose name ends with _live call the TSETMC API.
"""

import asyncio
import unittest
from dataclasses import astuple
from unittest import mock

import aiohttp
from pytse_client import tse_settings
from pytse_client.data.generate_indices_name import (
    build_indices,
    get_financial_indices,
    parse_index_title,
)
from pytse_client.scraper.symbol_scraper import (
    MarketSymbol,
    add_old_indexes_to_market_symbols,
    deduplicate_market_symbols,
    get_market_symbols_from_market_watch_page,
    get_symbol_ids,
    get_symbol_info,
    market_symbols_from_market_watch,
    match_search_results,
    remove_active_indexes_from_old,
)
from pytse_client.tsetmc_api.index import parse_indices
from pytse_client.tsetmc_api.instrument import parse_instrument_search
from pytse_client.tsetmc_api.market import parse_market_watch

FOLAD = MarketSymbol(
    code="IRO1FOLD0001",
    symbol="فولاد",
    name="فولاد مبارکه اصفهان",
    index="46348559193224090",
    old=[],
)


def as_tuples(symbols):
    # MarketSymbol.__eq__ only compares the symbol, compare every field
    return [astuple(symbol) for symbol in symbols]


# the other keys of a market watch row, the tests below do not use them
MARKET_WATCH_ROW = {
    "hEven": 122931,
    "pf": 5190.0,
    "pcl": 5150.0,
    "pdv": 5120.0,
    "ztt": 27226.0,
    "qtj": 1822800223.0,
    "qtc": 9381707847770.0,
    "pmn": 5120.0,
    "pmx": 5250.0,
    "py": 5270.0,
    "eps": 693.0,
    "bv": 1.0,
    "vc": 3423,
    "flow": 1,
    "csv": "27 ",
    "pMax": 5420.0,
    "pMin": 5120,
    "ztd": 1935000000000.0,
    "yVal": 300,
    "blDs": [],
}


class TestSymbolScraper(unittest.TestCase):
    def test_market_symbols_from_market_watch(self):
        rows = [
            {
                "lva": "فولاد",
                "lvc": "فولاد مباركه اصفهان",
                "insID": "IRO1FOLD0001",
                "insCode": "46348559193224090",
            },
            {
                "lva": "سرمايه‌گذاري",
                "lvc": "سرمايه‌گذاري‌ نمونه\t",
                "insID": "IRO1XXXX0001",
                "insCode": "1",
            },
            # bonds, options and other symbols ending with a number
            {
                "lva": "ضفلا1409",
                "lvc": "اختيارخ فولاد-3000-1404/11/08",
                "insID": "IRO9FOLD0C41",
                "insCode": "20215861245096550",
            },
        ]
        market_watch = parse_market_watch(
            {"marketwatch": [{**MARKET_WATCH_ROW, **row} for row in rows]}
        )
        self.assertEqual(
            as_tuples(market_symbols_from_market_watch(market_watch)),
            as_tuples(
                [
                    FOLAD,
                    MarketSymbol(
                        code="IRO1XXXX0001",
                        symbol="سرمایه‌گذاری",
                        name="سرمایهگذاری نمونه",
                        index="1",
                        old=[],
                    ),
                ]
            ),
        )

    def test_match_search_results(self):
        data = {
            "instrumentSearch": [
                {"insCode": "1", "lVal18AFC": "آبادا", "lastDate": 1},
                {"insCode": "2", "lVal18AFC": "آبادا", "lastDate": 0},
                {"insCode": "3", "lVal18AFC": "آباداح", "lastDate": 0},
                {"insCode": "4", "lVal18AFC": "آبادا", "lastDate": 1},
            ]
        }
        results = parse_instrument_search(data)
        active, old = match_search_results(results, "آبادا")
        self.assertEqual(active.ins_code, "1")
        self.assertEqual(old, ["2"])
        active, _ = match_search_results(results, "آبادا", preferred_index="4")
        self.assertEqual(active.ins_code, "4")
        active, old = match_search_results(results, "آباداح")
        self.assertIsNone(active)
        self.assertEqual(old, ["3"])

    def test_deduplicate_keeps_first(self):
        other = MarketSymbol("X", "فولاد", "other", "1", [])
        self.assertEqual(
            as_tuples(deduplicate_market_symbols([FOLAD, other])),
            as_tuples([FOLAD]),
        )

    def test_remove_active_indexes_from_old(self):
        symbols = [
            # renamed fund: its old symbol is now a company with a new
            # index, the fund's index is active under سافرون
            MarketSymbol("IRO5SKHZ0001", "سحرخیز", "company", "2", ["1"]),
            MarketSymbol("IRTKSAHR0001", "سافرون", "fund", "1", []),
            # deleted symbol whose index is active under its new symbol
            MarketSymbol("IRT3OXYF0001", "اکسیژن", "fund", "3", ["3"]),
            MarketSymbol("IRT3OXYF0001", "رواج", "fund", "3", []),
            # deleted symbol, its index stays in its old list
            MarketSymbol("IRO1SHOS0001", "شوش", "deleted", "4", ["4", "5"]),
            # old index of a symbol that no other symbol uses
            MarketSymbol("IRO1NBAB0001", "آبادا", "active", "6", ["7"]),
        ]
        self.assertEqual(
            [
                (symbol.symbol, symbol.old)
                for symbol in remove_active_indexes_from_old(symbols)
            ],
            [
                ("سحرخیز", []),
                ("سافرون", []),
                ("اکسیژن", []),
                ("رواج", []),
                ("شوش", ["4", "5"]),
                ("آبادا", ["7"]),
            ],
        )

    def test_failed_search_keeps_old_indexes(self):
        # the market watch symbol has no old indexes, the json has some
        market_watch_symbol = MarketSymbol(
            "IRO1KBIR0001", "شکبیر", "name", "69243469815198168", []
        )
        previous = MarketSymbol(
            "IRO1KBIR0001",
            "شکبیر",
            "name",
            "69243469815198168",
            ["56574323121551263"],
        )
        with mock.patch(
            "pytse_client.scraper.symbol_scraper._search_symbol",
            side_effect=aiohttp.ClientError("search failed"),
        ):
            [result] = asyncio.run(
                add_old_indexes_to_market_symbols(
                    [market_watch_symbol],
                    active_symbols={"شکبیر": "69243469815198168"},
                    previous={"شکبیر": previous},
                )
            )
        self.assertEqual(astuple(result), astuple(previous))

    def test_get_symbol_info_live(self):
        self.assertEqual(
            as_tuples([get_symbol_info("فولاد")]), as_tuples([FOLAD])
        )

    def test_get_symbol_info_with_old_index_live(self):
        info = get_symbol_info("آبادا")
        self.assertEqual(info.index, "37661500521100963")
        self.assertEqual(info.code, "IRO1NBAB0001")
        self.assertIn("18621338450655320", info.old)
        self.assertNotIn(info.index, info.old)

    def test_get_symbol_info_unknown_live(self):
        self.assertIsNone(get_symbol_info("ززززززز"))

    def test_get_symbol_ids_live(self):
        async def get_ids():
            async with aiohttp.ClientSession(
                headers=tse_settings.HEADERS
            ) as session:
                return await get_symbol_ids("آبادا", session)

        index, old_ids = asyncio.run(get_ids())
        self.assertEqual(index, "37661500521100963")
        self.assertIn("18621338450655320", old_ids)

    def test_market_watch_live(self):
        symbols = {
            s.symbol: s for s in get_market_symbols_from_market_watch_page()
        }
        self.assertGreater(len(symbols), 500)
        self.assertEqual(symbols["فولاد"], FOLAD)
        for symbol in symbols.values():
            self.assertFalse(symbol.symbol[-1].isdigit(), symbol)
            self.assertNotIn("ي", symbol.symbol + symbol.name)
            self.assertNotIn("ك", symbol.symbol + symbol.name)
            self.assertNotIn("‌", symbol.name)


class TestIndicesScraper(unittest.TestCase):
    def test_parse_index_title(self):
        self.assertEqual(
            parse_index_title("27-فلزات اساسي"), ("فلزات اساسي", 27)
        )
        self.assertEqual(
            parse_index_title("بيمه و بازنشسته66"), ("بيمه و بازنشسته", 66)
        )
        self.assertEqual(
            parse_index_title("شاخص قيمت(وزني-ارزشي)"),
            ("شاخص قيمت(وزنيارزشي)", ""),
        )

    def test_build_indices(self):
        flow1 = [
            {"insCode": "1", "lVal30": "35-حمل و نقل"},
            {"insCode": "2", "lVal30": "49-كاشي و سراميك"},
            {"insCode": "3", "lVal30": "60-حمل و نقل"},
        ]
        flow2 = [
            {"insCode": "4", "lVal30": "كاشي و سراميك"},
            {"insCode": "5", "lVal30": "شاخص كل فرابورس"},
        ]
        self.assertEqual(
            build_indices(
                [
                    parse_indices({"indexB1": flow1}),
                    parse_indices({"indexB1": flow2}),
                ]
            ),
            {
                "حمل و نقل": {"index": "3", "section_number": 60},
                "كاشي و سراميك": {"index": "2", "section_number": 49},
                "شاخص كل فرابورس": {"index": "5", "section_number": ""},
            },
        )

    def test_get_financial_indices_live(self):
        indices = get_financial_indices()
        self.assertEqual(
            indices["شاخص كل"],
            {"index": "32097828799138957", "section_number": ""},
        )
        self.assertEqual(
            indices["فلزات اساسي"],
            {"index": "32453344048876642", "section_number": 27},
        )
        self.assertEqual(
            indices["شاخص كل فرابورس"]["index"], "43685683301327984"
        )


if __name__ == "__main__":
    unittest.main()
