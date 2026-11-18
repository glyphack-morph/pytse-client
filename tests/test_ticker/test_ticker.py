"""
End to end tests of Ticker, they call the live tsetmc api.
"""

import datetime
import unittest
from unittest import mock

import pandas as pd
from pytse_client import Ticker, download
from pytse_client.ticker import ticker as ticker_module
from pytse_client.ticker.api_extractors import Order, TradeSummary
from pytse_client.tsetmc_api.closing_price import (
    fetch_recent_closing_price_daily_list,
)


class TestTicker(unittest.TestCase):
    def setUp(self) -> None:
        self.activate_symbol = "ذوب"
        return super().setUp()

    def tearDown(self) -> None:
        return super().tearDown()

    def test_option_trading(self):
        ticker = Ticker("", "816070469779688")
        ticker.title
        ticker.fulltitle

    def test_real_time_info_will_not_fail_with_deactivated_symbol(self):
        ticker = Ticker("", index="3823243780502959")
        self.assertRaises(
            RuntimeError,
            ticker.get_ticker_real_time_info_response,
        )

    def test_get_total_shares_history_on_activate_symbol(self):
        import asyncio

        # This should run without error
        res = asyncio.run(
            Ticker(self.activate_symbol).get_total_shares_history_async()
        )


class TestTickerNewApi(unittest.TestCase):
    """
    one test per api the Ticker uses, all for فولاد
    (insCode 46348559193224090)
    """

    symbol = "فولاد"
    index = "46348559193224090"

    @classmethod
    def setUpClass(cls) -> None:
        cls.ticker = Ticker(cls.symbol)

    def test_url(self):
        self.assertEqual(
            self.ticker.url, f"https://www.tsetmc.com/instInfo/{self.index}"
        )

    def test_get_last_trade_day(self):
        # api: MarketData/GetMarketOverview
        last_trade_day = Ticker.get_last_trade_day()
        self.assertIsInstance(last_trade_day, datetime.date)
        self.assertLessEqual(last_trade_day, datetime.date.today())
        self.assertGreater(
            last_trade_day, datetime.date.today() - datetime.timedelta(30)
        )

    def test_history(self):
        # api: ClosingPrice/GetClosingPriceDailyList
        history = self.ticker.history
        self.assertEqual(
            list(history.columns),
            [
                "date",
                "open",
                "high",
                "low",
                "adjClose",
                "value",
                "volume",
                "count",
                "yesterday",
                "close",
            ],
        )
        self.assertGreater(len(history), 1000)
        self.assertTrue(history["date"].is_monotonic_increasing)
        # days without any trade are not part of the history
        self.assertTrue((history["count"] > 0).all())
        # the last traded day of the daily history. Not get_last_trade_day:
        # while the market is open that is today, and the daily history
        # gets today's row only after the close.
        last_traded_day = max(
            day.date
            for day in fetch_recent_closing_price_daily_list(self.index)
            if day.trade_count > 0
        )
        self.assertEqual(self.ticker.trade_dates[-1], last_traded_day)

    def test_history_is_up_to_date(self):
        # api: ClosingPrice/GetClosingPriceDailyList/{insCode}/12
        history = self.ticker.history
        self.assertTrue(self.ticker._is_history_up_to_date(history))
        # a saved history without the last traded day is out of date
        self.assertFalse(self.ticker._is_history_up_to_date(history.iloc[:-1]))

    def test_saved_history_is_used(self):
        # the first Ticker saved the history csv, a second Ticker of the
        # same symbol reads it instead of downloading the history again
        with mock.patch.object(
            ticker_module, "download", side_effect=AssertionError
        ) as download_mock:
            ticker = Ticker(self.symbol)
        download_mock.assert_not_called()
        self.assertEqual(len(ticker.history), len(self.ticker.history))

    def test_arabic_letters_in_symbol(self):
        # شكبير with Arabic ي and ك is the symbol شکبیر, including the
        # history of its old index (it starts in 2011)
        history = download("شكبير")
        self.assertEqual(list(history), ["شکبیر"])
        self.assertLess(history["شکبیر"]["date"].iloc[0].year, 2012)

    def test_realtime_properties_request_only_what_they_need(self):
        not_needed = ["fetch_best_limits", "fetch_client_type", "fetch_etf"]
        with mock.patch.multiple(
            ticker_module,
            **{name: mock.DEFAULT for name in not_needed},
        ) as mocks:
            self.assertGreater(self.ticker.last_price, 0)
            self.assertGreater(self.ticker.market_cap, 0)
            self.assertIsInstance(self.ticker.p_e_ratio, float)
        for name in not_needed:
            mocks[name].assert_not_called()
        # فولاد is not a fund, its NAV is not requested
        with mock.patch.object(ticker_module, "fetch_etf") as fetch_etf:
            info = self.ticker.get_ticker_real_time_info_response()
        fetch_etf.assert_not_called()
        self.assertIsNone(info.nav)

    def test_instrument_info(self):
        # api: Instrument/GetInstrumentInfo
        ticker = self.ticker
        self.assertEqual(ticker.instrument_id, "IRO1FOLD0001")
        self.assertEqual(ticker.ci_sin, "IRO1FOLD0009")
        self.assertIn("فولاد", ticker.title)
        self.assertIn("فولاد", ticker.fulltitle)
        self.assertTrue(ticker.group_name)
        self.assertEqual(ticker.flow, "بورس")
        self.assertGreater(ticker.total_shares, 0)
        self.assertGreater(ticker.base_volume, 0)
        self.assertGreater(ticker.sta_max, ticker.sta_min)
        self.assertGreaterEqual(ticker.max_week, ticker.min_week)
        self.assertGreaterEqual(ticker.max_year, ticker.min_year)
        self.assertTrue(ticker.month_average_volume.isdigit())
        self.assertIsInstance(ticker.float_shares, float)
        self.assertIsInstance(ticker.eps, float)
        self.assertIsInstance(ticker.group_p_e_ratio, float)
        self.assertIsInstance(ticker.psr, float)
        self.assertIsInstance(ticker.p_e_ratio, float)
        self.assertIsInstance(ticker.p_s_ratio, float)

    def test_fiscal_year(self):
        # api: Codal/GetCodalPublisherBySymbol
        self.assertEqual(self.ticker.fiscal_year, "12/29")

    def test_fiscal_year_of_ticker_created_with_index(self):
        ticker = Ticker("", index=self.index)
        self.assertEqual(ticker.fiscal_year, "12/29")

    def test_real_time_info(self):
        # apis: ClosingPrice/GetClosingPriceInfo, BestLimits,
        # ClientType/GetClientType
        info = self.ticker.get_ticker_real_time_info_response()
        self.assertIn(
            info.state,
            {
                "مجاز",
                "مجاز-مسدود",
                "مجاز-متوقف",
                "مجاز-محفوظ",
                "ممنوع",
                "ممنوع-مسدود",
                "ممنوع-متوقف",
                "ممنوع-محفوظ",
            },
        )
        for price in [
            info.last_price,
            info.adj_close,
            info.yesterday_price,
            info.open_price,
            info.high_price,
            info.low_price,
        ]:
            self.assertIsInstance(price, int)
            self.assertGreater(price, 0)
        self.assertGreaterEqual(info.high_price, info.low_price)
        self.assertGreater(info.count, 0)
        self.assertGreater(info.volume, 0)
        self.assertGreater(info.value, 0)
        self.assertIsInstance(info.last_date, datetime.datetime)
        self.assertEqual(
            info.market_cap, info.adj_close * self.ticker.total_shares
        )
        # order book
        self.assertEqual(len(info.buy_orders), 5)
        self.assertEqual(len(info.sell_orders), 5)
        self.assertIsInstance(info.buy_orders[0], Order)
        self.assertEqual(info.best_demand_price, info.buy_orders[0].price)
        self.assertEqual(info.best_supply_price, info.sell_orders[0].price)
        # حقیقی حقوقی
        self.assertIsInstance(info.individual_trade_summary, TradeSummary)
        self.assertIsInstance(info.corporate_trade_summary, TradeSummary)
        self.assertGreater(info.individual_trade_summary.buy_count, 0)
        # not a fund
        self.assertIsNone(info.nav)
        self.assertIsNone(info.nav_date)

    def test_nav_of_fund(self):
        # api: Fund/GetETFByInsCode, for the fund كاريس
        fund = Ticker("", index="69067576215760005")
        self.assertIsInstance(fund.nav, int)
        self.assertGreater(fund.nav, 0)
        # Jalali date and time, like 1405/8/27 13:58:00
        self.assertRegex(
            fund.nav_date, r"^14\d\d/\d{1,2}/\d{1,2} \d\d:\d\d:\d\d$"
        )
        # funds have no psr, the api sends 0 for it
        self.assertIsNone(fund.psr)

    def test_missing_sector_pe_is_none(self):
        # the api sends 0 as the sector P/E of the fixed income fund
        # ياقوت (كاريس, a stock fund, has one)
        fund = Ticker("", index="1438514795814416")
        self.assertIsNone(fund.group_p_e_ratio)
        self.assertIsNone(fund.psr)

    def test_shareholders(self):
        # api: Shareholder/GetInstrumentShareHolderLast
        shareholders = self.ticker.shareholders
        self.assertEqual(
            list(shareholders.columns),
            ["id", "shareholder", "shares", "percentage", "change"],
        )
        self.assertFalse(shareholders.empty)
        self.assertGreater(shareholders["percentage"].sum(), 0)
        self.assertLessEqual(shareholders["percentage"].sum(), 100)

    def test_client_types(self):
        # api: ClientType/GetClientTypeHistory
        client_types = self.ticker.client_types
        self.assertGreater(len(client_types), 1000)
        for column in [
            "date",
            "individual_buy_count",
            "corporate_buy_count",
            "individual_sell_count",
            "corporate_sell_count",
            "individual_buy_vol",
            "corporate_buy_vol",
            "individual_sell_vol",
            "corporate_sell_vol",
            "individual_buy_value",
            "corporate_buy_value",
            "individual_sell_value",
            "corporate_sell_value",
            "individual_buy_mean_price",
            "individual_ownership_change",
        ]:
            self.assertIn(column, client_types.columns)
        last_day = client_types.iloc[0]
        self.assertEqual(
            last_day["individual_buy_vol"] + last_day["corporate_buy_vol"],
            last_day["individual_sell_vol"] + last_day["corporate_sell_vol"],
        )

    def test_trade_details(self):
        # api: Trade/GetTrade
        trades = self.ticker.get_trade_details()
        self.assertEqual(list(trades.columns), ["date", "volume", "price"])
        self.assertFalse(trades.empty)
        self.assertIsInstance(trades["date"].iloc[0], datetime.time)
        self.assertTrue((trades["volume"] > 0).all())

    def test_shareholders_history(self):
        # api: Shareholder/{insCode}/{date}
        history = self.ticker.get_shareholders_history(
            from_when=datetime.timedelta(days=7)
        )
        self.assertIsInstance(history, pd.DataFrame)
        self.assertFalse(history.empty)


def suite():
    test_suite = unittest.TestSuite()
    test_suite.addTest(
        unittest.TestLoader().loadTestsFromTestCase(TestTickerNewApi)
    )
    return test_suite


if __name__ == "__main__":
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite())
