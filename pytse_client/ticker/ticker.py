import asyncio
import datetime
import functools
import logging
import os
from dataclasses import dataclass
from typing import List, Optional

import aiohttp
import jdatetime
import pandas as pd
import requests
from pytse_client import (
    config,
    symbols_data,
    tse_settings,
    utils,
)
from pytse_client.download import download, download_ticker_client_types_record
from pytse_client.proxy.tsetmc import (
    get_day_shareholders_history,
    get_day_ticker_info_history,
)
from pytse_client.tse_settings import TSE_CLIENT_TYPE_DATA_URL
from pytse_client.tsetmc_api.best_limits import (
    Order,
    fetch_best_limits,
    orders_from_best_limits,
)
from pytse_client.tsetmc_api.client_type import (
    TradeSummary,
    corporate_trade_summary,
    fetch_client_type,
    individual_trade_summary,
)
from pytse_client.tsetmc_api.closing_price import (
    ClosingPriceInfo,
    fetch_closing_price_info,
    fetch_recent_closing_price_daily_list,
)
from pytse_client.tsetmc_api.codal import CodalPublisher, fetch_codal_publisher
from pytse_client.tsetmc_api.fund import fetch_etf
from pytse_client.tsetmc_api.instrument import (
    InstrumentHistory,
    InstrumentInfo,
    fetch_instrument_info,
)
from pytse_client.tsetmc_api.market import fetch_market_overview
from pytse_client.tsetmc_api.shareholder import Shareholder, fetch_shareholders
from pytse_client.tsetmc_api.trade import fetch_trades, unique_trades
from pytse_client.utils.decorators import catch
from pytse_client.utils.persian import replace_arabic

logger = logging.getLogger(config.LOGGER_NAME)
logger.addHandler(logging.NullHandler())


@dataclass
class RealtimeTickerInfo:
    date_time: datetime.datetime
    state: Optional[str]
    last_price: Optional[float]
    adj_close: Optional[float]
    yesterday_price: Optional[float]
    open_price: Optional[float]
    high_price: Optional[float]
    low_price: Optional[float]
    count: Optional[int]
    volume: Optional[int]
    value: Optional[int]
    last_date: Optional[datetime.datetime]
    best_demand_vol: Optional[int]
    best_demand_price: Optional[float]
    best_supply_vol: Optional[int]
    best_supply_price: Optional[float]
    sell_orders: Optional[List[Order]]
    buy_orders: Optional[List[Order]]
    individual_trade_summary: Optional[TradeSummary]
    corporate_trade_summary: Optional[TradeSummary]
    nav: Optional[int]
    nav_date: Optional[str]
    # ارزش بازار
    market_cap: Optional[int]


class Ticker:
    def __init__(
        self,
        symbol: str,
        index: Optional[str] = None,
        adjust: bool = False,
    ):
        # the symbols json uses Persian letters (ی, ک), accept Arabic ones
        symbol = replace_arabic(symbol.strip())
        determined_symbol_index = index or symbols_data.get_ticker_index(
            symbol
        )
        if determined_symbol_index is None:
            raise ValueError(
                f"""Symbol {symbol} not found, if you are trying to use
                             a symbol which is removed from the tse website
                             provide it's index manually:
                             ticker = tse.Ticker("", index="25165947991415904")
                             """
            )
        self._index = determined_symbol_index
        self.symbol = symbol if index is None else self._index
        self.adjust = adjust
        self.daily_records_csv_path = (
            f"{config.DATA_BASE_PATH}/{self.symbol}.csv"
        )
        self.adjusted_daily_records_csv_path = (
            f"{config.DATA_BASE_PATH}/{self.symbol}-ت.csv"
        )
        # page of the ticker on www.tsetmc.com
        self._url = tse_settings.TSE_TICKER_ADDRESS.format(self._index)
        self._url_new = tse_settings.TSE_INSTRUMENT_INFO.format(self._index)
        self._info_url = tse_settings.TSE_CLOSING_PRICE_INFO_URL.format(
            self._index
        )
        self._client_types_url = TSE_CLIENT_TYPE_DATA_URL.format(self._index)
        csv_path = (
            self.adjusted_daily_records_csv_path
            if self.adjust
            else self.daily_records_csv_path
        )
        history = None
        if os.path.exists(csv_path):
            history = self.from_file()
            if not self._is_history_up_to_date(history):
                history = None
        if history is None:
            history = download(
                symbols=self.symbol,
                adjust=self.adjust,
                write_to_csv=True,
            )[self.symbol]
        self._history: pd.DataFrame = history

    def _is_history_up_to_date(self, history: pd.DataFrame) -> bool:
        """
        True when the daily history has no trading day after the last row
        of the saved history. The market overview (get_last_trade_day)
        gives today as soon as the market opens, but the daily history only
        gets today's row after the close, so the saved history is compared
        with the last 12 days of the daily history instead.
        """
        if history.empty:
            return False
        last_saved = history["date"].iloc[-1].date()
        recent_days = fetch_recent_closing_price_daily_list(self._index)
        if not recent_days:
            return True
        if any(
            day.date > last_saved and day.trade_count > 0
            for day in recent_days
        ):
            return False
        # days without a trade are not saved, so the 12 days must reach
        # back to the last saved day to know nothing was traded since
        return min(day.date for day in recent_days) <= last_saved

    def from_file(self) -> pd.DataFrame:
        if self.adjust:
            history = pd.read_csv(self.adjusted_daily_records_csv_path)
        else:
            history = pd.read_csv(self.daily_records_csv_path)
        history["date"] = pd.to_datetime(history["date"])
        return history

    @property
    def history(self):
        return self._history

    @property
    def url(self):
        return self._url

    @property
    def index(self):
        return self._index

    @property
    def instrument_id(self):
        """
        instrument id of a ticker is unique and used for calling
        some apis from tsetmc
        """
        return self._instrument_info.isin

    @property
    def ci_sin(self):
        """
        instrument id of a ticker is like instrument_id and used for calling
        some apis from tsetmc
        """
        return self._instrument_info.company_isin

    @property
    def title(self) -> str:
        """
        Symbol title in persian
        """
        return replace_arabic(self._instrument_info.name.split("-")[0])

    @property
    def fulltitle(self) -> str:
        """
        Symbol title with it's market in persian
        """
        return replace_arabic(self._instrument_info.name)

    @property
    def group_name(self) -> str:
        return self._instrument_info.sector.name

    @property
    def p_e_ratio(self) -> Optional[float]:
        """
        Notes on usage: tickers like آسام does not have p/e
        """
        adj_close = self._realtime_info(prices=True).adj_close
        eps = self.eps
        if adj_close is None or eps is None or eps == 0:
            return None
        return adj_close / eps

    @property
    def group_p_e_ratio(self) -> Optional[float]:
        """
        Notes on usage: tickers like وملت does not have group P/E (gpe)
        """
        # the api sends 0 when there is no value (e.g. funds)
        return self._instrument_info.eps.sector_pe or None

    @property
    def eps(self) -> Optional[float]:
        """
        Notes on usage: tickers like آسام does not have eps
        """
        return self._instrument_info.eps.estimated_eps

    @property
    def p_s_ratio(self) -> Optional[float]:
        """
        Notes on usage: tickers like آسام does not have p/s
        """
        adj_close = self._realtime_info(prices=True).adj_close
        psr = self.psr
        if adj_close is None or psr is None or psr == 0:
            return None
        return adj_close / psr

    @property
    def psr(self) -> Optional[float]:
        """
        Notes on usage: tickers like آسام does not have psr
        """
        # the api sends 0 when there is no value (e.g. funds)
        return self._instrument_info.eps.psr or None

    @property
    def total_shares(self) -> float:
        return float(self._instrument_info.total_shares)

    @property
    def base_volume(self) -> float:
        return float(self._instrument_info.base_volume)

    @property
    def fiscal_year(self) -> Optional[str]:
        """
        سال مالی, end of the fiscal year as month/day, e.g. "12/29"
        """
        publisher = self._codal_publisher
        if publisher is None:
            return None
        return publisher.financial_year or None

    @property
    def flow(self) -> str:
        """
        عنوان بازار
        """
        return self._flow_name(str(self._instrument_info.flow))

    @property
    @catch(TypeError, ValueError)
    def sta_max(self) -> float:
        """
        حداکثر قیمت مجاز
        """
        threshold = self._instrument_info.static_threshold
        return float(threshold.max_price) if threshold else None

    @property
    @catch(TypeError, ValueError)
    def sta_min(self) -> float:
        """
        حداقل قیمت مجاز
        """
        threshold = self._instrument_info.static_threshold
        return float(threshold.min_price) if threshold else None

    @property
    @catch(TypeError, ValueError)
    def min_week(self) -> float:
        """
        حداقل قیمت هفته اخیر
        """
        return float(self._instrument_info.min_week)

    @property
    @catch(TypeError, ValueError)
    def max_week(self) -> float:
        """
        حداکثر قیمت هفته اخیر
        """
        return float(self._instrument_info.max_week)

    @property
    @catch(TypeError, ValueError)
    def min_year(self) -> float:
        """
        حداقل قیمت بازه سال
        """
        return float(self._instrument_info.min_year)

    @property
    @catch(TypeError, ValueError)
    def max_year(self) -> float:
        """
        حداکثر قیمت بازه سال
        """
        return float(self._instrument_info.max_year)

    @property
    def month_average_volume(self) -> str:
        """
        میانگین حجم ماه
        """
        return str(int(self._instrument_info.month_average_volume))

    @property
    @catch(TypeError, ValueError)
    def float_shares(self) -> float:
        """
        درصد سهام شناور
        """
        return float(self._instrument_info.free_float)

    @property
    def client_types(self):
        client_types = download_ticker_client_types_record(self._index)
        if client_types is None:
            raise RuntimeError("cannot download client types data try again")
        return client_types

    @property
    def trade_dates(self) -> List[datetime.date]:
        trade_dates = map(
            lambda datetime_val: datetime_val.date(),
            pd.to_datetime(self._history["date"]),
        )
        return list(trade_dates)

    @property
    def shareholders(self) -> pd.DataFrame:
        """
        latest major shareholders (سهامداران عمده)
        columns: id, shareholder, shares, percentage, change
        """
        rows = fetch_shareholders(self._index)
        # shares and change are float64 columns like before
        return pd.DataFrame(
            [
                [
                    row.share_id,
                    row.name,
                    float(row.shares),
                    row.percentage,
                    float(row.change_amount),
                ]
                for row in rows
            ],
            columns=["id", "shareholder", "shares", "percentage", "change"],
        )

    def get_shareholders_history(
        self,
        from_when=datetime.timedelta(days=90),
        to_when=datetime.datetime.now(),
        only_trade_days=True,
        session=None,
    ) -> pd.DataFrame:
        """
        a helper function to use shareholders_history_async
        """
        return asyncio.run(
            self.get_shareholders_history_async(
                from_when,
                to_when,
                only_trade_days,
                session,
            ),
        )

    async def get_shareholders_history_async(
        self,
        from_when=datetime.timedelta(days=90),
        to_when=datetime.datetime.now(),
        only_trade_days=True,
        session=None,
    ) -> pd.DataFrame:
        requested_dates = utils.datetime_range(to_when - from_when, to_when)
        session_created = False
        if not session:
            session_created = True
            conn = aiohttp.TCPConnector(limit=25)
            session = aiohttp.ClientSession(connector=conn)
        tasks = []
        filtered_dates = list(
            filter(
                lambda date: not only_trade_days
                or (only_trade_days and date.date() in self.trade_dates),
                requested_dates,
            )
        )
        for date in filtered_dates:
            tasks.append(
                get_day_shareholders_history(self._index, date, session)
            )
        all_tickers_shareholders: List[List[Shareholder]] = (
            await asyncio.gather(*tasks)
        )
        if session_created is True:
            await session.close()

        rows = []
        for ticker_shareholders, info_date in zip(
            all_tickers_shareholders, filtered_dates
        ):
            for shareholder in ticker_shareholders:
                rows.append(
                    [
                        info_date,
                        shareholder.share_id,
                        # float64 column like before
                        float(shareholder.shares),
                        shareholder.percentage,
                        shareholder.company_isin,
                        shareholder.name,
                        shareholder.change,
                    ]
                )
        return pd.DataFrame(
            data=rows,
            columns=[
                "date",
                "shareholder_id",
                "shareholder_shares",
                "shareholder_percentage",
                "shareholder_instrument_id",
                "shareholder_name",
                "change",
            ],
        )

    async def get_total_shares_history_async(
        self,
        from_when=datetime.timedelta(days=60),
        to_when=datetime.datetime.now(),
        only_open_days=True,
        session=None,
    ) -> pd.DataFrame:
        requested_dates = map(
            lambda datetime_val: datetime_val.date(),
            utils.datetime_range(to_when - from_when, to_when),
        )
        session_created = False
        if not session:
            session_created = True
            conn = aiohttp.TCPConnector(limit=25)
            session = aiohttp.ClientSession(connector=conn)
        tasks = []
        filtered_dates = list(
            filter(
                lambda date: not only_open_days
                or (only_open_days and date in self.trade_dates),
                requested_dates,
            )
        )
        for date in filtered_dates:
            tasks.append(
                get_day_ticker_info_history(self._index, date, session)
            )
        instrument_history: List[InstrumentHistory] = await asyncio.gather(
            *tasks
        )
        if session_created is True:
            await session.close()

        rows = []
        for instrument_day_data, date in zip(
            instrument_history, filtered_dates
        ):
            rows.append(
                [
                    date,
                    # float64 column like before
                    float(instrument_day_data.total_shares),
                ]
            )
        return pd.DataFrame(
            data=rows,
            columns=["date", "total_shares"],
        )

    @property
    def state(self):
        return self._realtime_info(prices=True).state

    @property
    def last_price(self):
        return self._realtime_info(prices=True).last_price

    @property
    def adj_close(self):
        return self._realtime_info(prices=True).adj_close

    @property
    def yesterday_price(self):
        return self._realtime_info(prices=True).yesterday_price

    @property
    def open_price(self):
        return self._realtime_info(prices=True).open_price

    @property
    def high_price(self):
        return self._realtime_info(prices=True).high_price

    @property
    def low_price(self):
        return self._realtime_info(prices=True).low_price

    @property
    def count(self):
        return self._realtime_info(prices=True).count

    @property
    def volume(self):
        return self._realtime_info(prices=True).volume

    @property
    def value(self):
        return self._realtime_info(prices=True).value

    @property
    def last_date(self):
        return self._realtime_info(prices=True).last_date

    @property
    def best_demand_vol(self):
        return self._realtime_info(orders=True).best_demand_vol

    @property
    def best_demand_price(self):
        return self._realtime_info(orders=True).best_demand_price

    @property
    def best_supply_vol(self):
        return self._realtime_info(orders=True).best_supply_vol

    @property
    def best_supply_price(self):
        return self._realtime_info(orders=True).best_supply_price

    @property
    def nav(self):
        return self._realtime_info(nav=True).nav

    @property
    def market_cap(self):
        return self._realtime_info(prices=True).market_cap

    @property
    def nav_date(self):
        return self._realtime_info(nav=True).nav_date

    @classmethod
    def get_last_trade_day(cls) -> datetime.date:
        return fetch_market_overview().last_trade_date

    def get_ticker_real_time_info_response(self) -> RealtimeTickerInfo:
        """
        notes on usage:
        - Real time data might not be always available
        check for None values before usage
        """
        return self._realtime_info(
            prices=True, orders=True, client_types=True, nav=True
        )

    def _realtime_info(
        self,
        prices: bool = False,
        orders: bool = False,
        client_types: bool = False,
        nav: bool = False,
    ) -> RealtimeTickerInfo:
        """
        Realtime info built from only the apis that are asked for, so a
        property like last_price sends one request instead of four. The
        fields of the parts that are not asked for are None.

        prices: ClosingPrice/GetClosingPriceInfo (state, prices, count,
            volume, value, last_date, market_cap)
        orders: BestLimits (best_* and the buy and sell orders)
        client_types: ClientType/GetClientType (trade summaries)
        nav: Fund/GetETFByInsCode, only for funds (nav, nav_date)
        """
        if not self.__is_active():
            raise RuntimeError(
                f"Cannot get realtime data from inactive ticker {self.symbol}"
            )
        closing_price = best_limits = client_type = None
        session = utils.requests_retry_session()
        try:
            if prices:
                closing_price = fetch_closing_price_info(
                    self._index, session=session
                )
            if orders:
                best_limits = fetch_best_limits(self._index, session=session)
            if client_types:
                client_type = fetch_client_type(self._index, session=session)
        finally:
            session.close()
        nav_value, nav_date = self._get_nav() if nav else (None, None)

        price_fields = self._price_fields(closing_price)
        buy_orders, sell_orders = (
            orders_from_best_limits(best_limits) if orders else (None, None)
        )
        return RealtimeTickerInfo(
            datetime.datetime.now(),
            **price_fields,
            best_demand_vol=buy_orders[0].volume if buy_orders else None,
            best_demand_price=buy_orders[0].price if buy_orders else None,
            best_supply_vol=sell_orders[0].volume if sell_orders else None,
            best_supply_price=sell_orders[0].price if sell_orders else None,
            buy_orders=buy_orders,
            sell_orders=sell_orders,
            individual_trade_summary=(
                individual_trade_summary(client_type) if client_types else None
            ),
            corporate_trade_summary=(
                corporate_trade_summary(client_type) if client_types else None
            ),
            nav=nav_value,
            nav_date=nav_date,
        )

    def _price_fields(self, closing_price: Optional[ClosingPriceInfo]):
        """fields of RealtimeTickerInfo that come from the price box"""
        if closing_price is None:
            return dict(
                state=None,
                last_price=None,
                adj_close=None,
                yesterday_price=None,
                open_price=None,
                high_price=None,
                low_price=None,
                count=None,
                volume=None,
                value=None,
                last_date=None,
                market_cap=None,
            )
        instrument_state = closing_price.instrument_state
        state_code = instrument_state.code if instrument_state else None
        state = (
            self._instrument_state(state_code) or instrument_state.title
            if state_code
            else None
        )
        if closing_price.date and closing_price.time:
            last_date = datetime.datetime.combine(
                closing_price.date, closing_price.time
            )
        else:
            last_date = None
        adj_close = closing_price.closing_price
        return dict(
            state=state,
            last_price=closing_price.last_price,
            adj_close=adj_close,
            yesterday_price=closing_price.yesterday_price,
            open_price=closing_price.first_price,
            high_price=closing_price.high_price,
            low_price=closing_price.low_price,
            count=closing_price.trade_count,
            volume=closing_price.volume,
            value=closing_price.value,
            last_date=last_date,
            market_cap=(
                adj_close * self.total_shares
                if adj_close is not None
                else None
            ),
        )

    @property
    def _is_fund(self) -> bool:
        # the site only asks for the NAV of instruments whose ISIN starts
        # with IRT (funds), the api answers 500 for the others
        return (self._instrument_info.isin or "").startswith("IRT")

    def _get_nav(self):
        """
        NAV (قیمت ابطال) of a fund and its date as a Jalali string like
        "1405/8/27 13:58:00", (None, None) when the instrument is not a
        fund.
        """
        if not self._is_fund:
            return None, None
        # do not retry on server errors, the api answers 500 when it has no
        # NAV for the fund
        session = utils.requests_retry_session(retries=2, status_forcelist=())
        try:
            etf = fetch_etf(self._index, session=session, timeout=10)
        except (requests.RequestException, ValueError):
            return None, None
        finally:
            session.close()
        if etf is None or etf.redemption_nav is None:
            return None, None
        nav_date = None
        if etf.date and etf.time:
            jalali = jdatetime.date.fromgregorian(date=etf.date)
            nav_date = (
                f"{jalali.year}/{jalali.month}/{jalali.day} "
                f"{etf.time:%H:%M:%S}"
            )
        return etf.redemption_nav, nav_date

    @functools.cached_property
    def _instrument_info(self) -> InstrumentInfo:
        return fetch_instrument_info(self._index)

    @functools.cached_property
    def _codal_publisher(self) -> Optional[CodalPublisher]:
        """
        company introduction (معرفی) from codal, None for instruments that
        are not companies (funds, bonds, options...)
        """
        session = utils.requests_retry_session(retries=2)
        try:
            return fetch_codal_publisher(
                self._instrument_info.symbol, session=session, timeout=10
            )
        except (requests.RequestException, ValueError):
            return None
        finally:
            session.close()

    @property
    def _shareholders_url(self) -> str:
        return tse_settings.TSE_SHAREHOLDERS_URL.format(self._index)

    def _instrument_state(self, state_code) -> str:
        states = {
            "I ": "ممنوع",
            "A ": "مجاز",
            "AG": "مجاز-مسدود",
            "AS": "مجاز-متوقف",
            "AR": "مجاز-محفوظ",
            "IG": "ممنوع-مسدود",
            "IS": "ممنوع-متوقف",
            "IR": "ممنوع-محفوظ",
        }
        return states.get(state_code, "")

    def _flow_name(self, flow_code) -> str:
        flows = {
            "0": "عمومی - مشترک بین بورس و فرابورس",
            "1": "بورس",
            "2": "فرابورس",
            "3": "آتی",
            "4": "پایه فرابورس",
            "5": "پایه فرابورس (منتشر نمی شود)",
        }
        return flows.get(flow_code, "")

    def get_trade_details(self):
        """
        trades of the current trading day (canceled trades are skipped)
        columns: date (time of the trade), volume, price
        """
        trades = sorted(
            unique_trades(fetch_trades(self.index)),
            key=lambda trade: trade.number,
        )
        # price is a float64 column like before
        rows = [
            [trade.time, trade.volume, float(trade.price)] for trade in trades
        ]
        return pd.DataFrame(rows, columns=["date", "volume", "price"])

    def __is_active(self):
        """
        Check if ticker is in active state so new data comes in.
        Deactivated symbols have message
        نماد قدیمی حذف شده
        in their name.
        Returns: True if the symbol is in active state
        """
        most_recent_index = symbols_data.get_ticker_index(self.symbol)
        if most_recent_index is None:
            # ticker is created with an index, it is deactivated when it is
            # an old index of a symbol
            return not any(
                self._index in symbol_info.get("old", [])
                for symbol_info in symbols_data.symbols_information().values()
            )
        old_indexes = symbols_data.get_ticker_old_index(self.symbol)
        return most_recent_index not in old_indexes
