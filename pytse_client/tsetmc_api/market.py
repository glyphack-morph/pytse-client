"""Market wide endpoints: market overview, market watch and the key
statistics of every instrument.

tse_settings constants and the pages that call them:

- TSE_GET_LAST_TRADE_DAY, MarketData/GetMarketOverview/1: home page
  (https://www.tsetmc.com/), tab "در یک نگاه", box
  "بازار نقدی بورس در یک نگاه"; also polled by the "نمای کلی از بازار" box
  of instInfo and History pages.
- MARKET_WATCH_URL, ClosingPrice/GetMarketWatch: market watch
  (https://www.tsetmc.com/marketwatchnew), loaded with the page.
- KEY_STATS_URL, MarketData/GetInstValueAllInstAllParam: no page sends it
  today; the market watch filters of the site code have it (see
  tse_settings).

Prices and values are in rial, volumes in shares.
"""

import datetime
from dataclasses import dataclass
from typing import Any, List, Optional, Union

import requests
from pytse_client import tse_settings
from pytse_client.tsetmc_api._convert import (
    number_text_to_float,
    to_date,
    to_optional_bool,
    to_optional_date,
    to_optional_float,
    to_optional_int,
    to_optional_time,
    to_time,
)
from pytse_client.utils.request_session import get_json

# ---------------------------------------------------------------------------
# MarketData/GetMarketOverview/{flow} (TSE_GET_LAST_TRADE_DAY)


@dataclass(frozen=True, slots=True)
class MarketOverview:
    """Overview of a market (key marketOverview); the library asks for
    flow 1, the stock exchange (بورس)."""

    # marketActivityDEven: last trading day of the market, the date of
    # "اطلاعات قیمت"
    last_trade_date: datetime.date
    # marketActivityHEven: time of "اطلاعات قیمت"
    last_trade_time: Optional[datetime.time] = None
    # indexLastValue: شاخص کل
    index_value: Optional[float] = None
    # indexChange: change of شاخص کل since the previous day
    index_change: Optional[float] = None
    # indexEqualWeightedLastValue: شاخص کل (هم وزن)
    equal_weighted_index_value: Optional[float] = None
    # indexEqualWeightedChange: change of شاخص کل (هم وزن)
    equal_weighted_index_change: Optional[float] = None
    # marketActivityZTotTran: تعداد معاملات
    trade_count: Optional[int] = None
    # marketActivityQTotTran: حجم معاملات, shares
    trade_volume: Optional[int] = None
    # marketActivityQTotCap: ارزش معاملات, rial
    trade_value: Optional[int] = None
    # marketValue: ارزش بازار, rial
    market_value: Optional[int] = None
    # marketValueBase: ارزش بازار پایه, rial; shown for fara bourse
    # (flow 2) only, 0 for flow 1
    base_market_value: Optional[int] = None
    # marketState: state code of the market, e.g. "F" (closed)
    state: Optional[str] = None
    # marketStateTitle: وضعیت بازار, e.g. "بسته"
    state_title: Optional[str] = None
    # lastDataDEven: 0 (no date) in every answer seen
    last_data_date: Optional[datetime.date] = None
    # lastDataHEven: 0 in every answer seen
    last_data_time: Optional[datetime.time] = None


def parse_market_overview(data: Any) -> MarketOverview:
    """Parse the JSON of MarketData/GetMarketOverview/{flow}."""
    overview = data["marketOverview"]
    return MarketOverview(
        last_trade_date=to_date(overview["marketActivityDEven"]),
        last_trade_time=to_optional_time(overview.get("marketActivityHEven")),
        index_value=to_optional_float(overview.get("indexLastValue")),
        index_change=to_optional_float(overview.get("indexChange")),
        equal_weighted_index_value=to_optional_float(
            overview.get("indexEqualWeightedLastValue")
        ),
        equal_weighted_index_change=to_optional_float(
            overview.get("indexEqualWeightedChange")
        ),
        trade_count=to_optional_int(overview.get("marketActivityZTotTran")),
        trade_volume=to_optional_int(overview.get("marketActivityQTotTran")),
        trade_value=to_optional_int(overview.get("marketActivityQTotCap")),
        market_value=to_optional_int(overview.get("marketValue")),
        base_market_value=to_optional_int(overview.get("marketValueBase")),
        state=overview.get("marketState"),
        state_title=overview.get("marketStateTitle"),
        last_data_date=to_optional_date(overview.get("lastDataDEven")),
        last_data_time=to_optional_time(overview.get("lastDataHEven")),
    )


def fetch_market_overview(
    session: Optional[requests.Session] = None, timeout: float = 30
) -> MarketOverview:
    """GET and parse TSE_GET_LAST_TRADE_DAY."""
    return parse_market_overview(
        get_json(
            tse_settings.TSE_GET_LAST_TRADE_DAY,
            session=session,
            timeout=timeout,
        )
    )


# ---------------------------------------------------------------------------
# ClosingPrice/GetMarketWatch (MARKET_WATCH_URL)


@dataclass(frozen=True, slots=True)
class MarketWatchBestLimit:
    """One level of the order book of a market watch row (blDs)."""

    # n: level, 1 is the best price
    level: int
    # zmd: تعداد خرید, number of buy orders
    buy_count: int
    # qmd: حجم خرید, shares
    buy_volume: int
    # pmd: قیمت خرید, rial
    buy_price: int
    # pmo: قیمت فروش, rial
    sell_price: int
    # qmo: حجم فروش, shares
    sell_volume: int
    # zmo: تعداد فروش, number of sell orders
    sell_count: int
    # rid: id of the last change of this level
    ref_id: Optional[int] = None


@dataclass(frozen=True, slots=True)
class MarketWatchInstrument:
    """One row of the market watch (key marketwatch): today's prices of
    an instrument. The short keys carry the data; the long ones (pClosing,
    pDrCotVal, ...) are 0 in every row seen."""

    # insCode: instrument code
    ins_code: str
    # insID: کد 12 رقمی نماد (ISIN of the symbol), e.g. "IRO1FOLD0001"
    isin: Optional[str]
    # lva: نماد (symbol), Arabic ي and ك
    symbol: Optional[str]
    # lvc: نام (name), Arabic ي and ك
    name: Optional[str]
    # hEven: time of the last change of the row
    time: datetime.time
    # pf: اولین قیمت (first price), rial
    first_price: int
    # pcl: قیمت پایانی (closing price), rial
    closing_price: int
    # pdv: آخرین معامله (last trade price), rial
    last_price: int
    # ztt: تعداد معاملات (number of trades)
    trade_count: int
    # qtj: حجم معاملات (volume), shares
    volume: int
    # qtc: ارزش معاملات (value), rial
    value: int
    # pmn: کمترین قیمت (low), rial
    low_price: int
    # pmx: بیشترین قیمت (high), rial
    high_price: int
    # py: قیمت دیروز (yesterday's closing price), rial
    yesterday_price: int
    # eps: EPS, rial
    eps: float
    # bv: حجم مبنا (base volume), shares
    base_volume: int
    # vc: number of visits of the symbol page
    visit_count: int
    # flow: market, 1 بورس, 2 فرابورس, 3 derivatives, 4 پایه فرابورس,
    # ...
    flow: int
    # csv: کد گروه صنعت (sector code), padded with a space, e.g. "27 "
    sector_code: str
    # pMax: upper price threshold (قیمت مجاز), rial
    max_allowed_price: int
    # pMin: lower price threshold (قیمت مجاز), rial
    min_allowed_price: int
    # ztd: تعداد سهام (total shares)
    total_shares: int
    # yVal: instrument type code, e.g. 300 for a share
    instrument_type: int
    # blDs: the best 5 order book levels (asked for with
    # withBestLimits=true)
    best_limits: List[MarketWatchBestLimit]
    # pe: P/E, sent as text, None when the instrument has none
    pe: Optional[float] = None
    # pmd: best buy price (قیمت خرید of level 1), rial
    best_buy_price: Optional[int] = None
    # pmo: best sell price (قیمت فروش of level 1), rial
    best_sell_price: Optional[int] = None
    # pc: تغییر آخرین معامله, change of the last price, rial
    last_price_change: Optional[int] = None
    # pcpc: تغییر قیمت پایانی, change of the closing price, rial
    closing_price_change: Optional[int] = None
    # cGrValCot: board code (کد تابلو), e.g. "N1"
    board_code: Optional[str] = None
    # yMarNSC: market code, e.g. "NO"
    market_code: Optional[str] = None
    # pRedTran: NAV ابطال (redemption NAV) of funds, 0 for others, rial
    nav: Optional[int] = None
    # buyOP: موقعیت های باز (open positions) of options and futures
    open_positions: Optional[int] = None
    # id: 0 in every row seen
    id: Optional[int] = None
    # dEven: 0 (no date) in every row seen
    date: Optional[datetime.date] = None
    # pClosing: 0 in every row seen, see closing_price (pcl)
    p_closing: Optional[int] = None
    # iClose: false in every row seen
    i_close: Optional[bool] = None
    # yClose: false in every row seen
    y_close: Optional[bool] = None
    # pDrCotVal: 0 in every row seen, see last_price (pdv)
    p_dr_cot_val: Optional[int] = None
    # zTotTran: 0 in every row seen, see trade_count (ztt)
    z_tot_tran: Optional[int] = None
    # qTotTran5J: 0 in every row seen, see volume (qtj)
    q_tot_tran5_j: Optional[int] = None
    # qTotCap: 0 in every row seen, see value (qtc)
    q_tot_cap: Optional[int] = None


def _parse_market_watch_best_limit(row: Any) -> MarketWatchBestLimit:
    return MarketWatchBestLimit(
        level=int(row["n"]),
        buy_count=int(row["zmd"]),
        buy_volume=int(row["qmd"]),
        buy_price=int(row["pmd"]),
        sell_price=int(row["pmo"]),
        sell_volume=int(row["qmo"]),
        sell_count=int(row["zmo"]),
        ref_id=row.get("rid"),
    )


def _parse_market_watch_instrument(row: Any) -> MarketWatchInstrument:
    return MarketWatchInstrument(
        ins_code=str(row["insCode"]),
        isin=row["insID"],
        symbol=row["lva"],
        name=row["lvc"],
        time=to_time(row["hEven"]),
        first_price=int(row["pf"]),
        closing_price=int(row["pcl"]),
        last_price=int(row["pdv"]),
        trade_count=int(row["ztt"]),
        volume=int(row["qtj"]),
        value=int(row["qtc"]),
        low_price=int(row["pmn"]),
        high_price=int(row["pmx"]),
        yesterday_price=int(row["py"]),
        eps=float(row["eps"]),
        base_volume=int(row["bv"]),
        visit_count=int(row["vc"]),
        flow=int(row["flow"]),
        sector_code=row["csv"],
        max_allowed_price=int(row["pMax"]),
        min_allowed_price=int(row["pMin"]),
        total_shares=int(row["ztd"]),
        instrument_type=int(row["yVal"]),
        best_limits=[
            _parse_market_watch_best_limit(level)
            for level in row["blDs"] or []
        ],
        pe=number_text_to_float(row.get("pe")),
        best_buy_price=to_optional_int(row.get("pmd")),
        best_sell_price=to_optional_int(row.get("pmo")),
        last_price_change=to_optional_int(row.get("pc")),
        closing_price_change=to_optional_int(row.get("pcpc")),
        board_code=row.get("cGrValCot"),
        market_code=row.get("yMarNSC"),
        nav=to_optional_int(row.get("pRedTran")),
        open_positions=to_optional_int(row.get("buyOP")),
        id=row.get("id"),
        date=to_optional_date(row.get("dEven")),
        p_closing=to_optional_int(row.get("pClosing")),
        i_close=to_optional_bool(row.get("iClose")),
        y_close=to_optional_bool(row.get("yClose")),
        p_dr_cot_val=to_optional_int(row.get("pDrCotVal")),
        z_tot_tran=to_optional_int(row.get("zTotTran")),
        q_tot_tran5_j=to_optional_int(row.get("qTotTran5J")),
        q_tot_cap=to_optional_int(row.get("qTotCap")),
    )


def parse_market_watch(data: Any) -> List[MarketWatchInstrument]:
    """Parse the JSON of ClosingPrice/GetMarketWatch, one row per
    instrument."""
    return [
        _parse_market_watch_instrument(row)
        for row in data["marketwatch"] or []
    ]


def fetch_market_watch(
    session: Optional[requests.Session] = None, timeout: float = 120
) -> List[MarketWatchInstrument]:
    """GET and parse MARKET_WATCH_URL (thousands of rows)."""
    return parse_market_watch(
        get_json(
            tse_settings.MARKET_WATCH_URL, session=session, timeout=timeout
        )
    )


# ---------------------------------------------------------------------------
# MarketData/GetInstValueAllInstAllParam (KEY_STATS_URL)


@dataclass(frozen=True, slots=True)
class InstrumentStatistic:
    """One statistic of one instrument (key instValueAllInstAllParam), the
    old آمارهای کلیدی (key statistics)."""

    # insCode: instrument code
    ins_code: str
    # dataType: id of the statistic, see
    # pytse_client/ticker_statisticals/key_stats.py
    stat_id: int
    # dataValue: value of the statistic, sent as text; int when the text
    # has no decimal point ("6042"), float otherwise ("0.000000")
    value: Union[int, float]
    # dEven: day of the statistics
    date: Optional[datetime.date] = None


def _number_text(text: str) -> Union[int, float]:
    if "." in text or "e" in text or "E" in text:
        return float(text)
    return int(text)


def parse_key_stats(data: Any) -> List[InstrumentStatistic]:
    """Parse the JSON of MarketData/GetInstValueAllInstAllParam (about
    340k rows)."""
    return [
        InstrumentStatistic(
            ins_code=str(row["insCode"]),
            stat_id=int(row["dataType"]),
            value=_number_text(row["dataValue"]),
            date=to_optional_date(row.get("dEven")),
        )
        for row in data["instValueAllInstAllParam"] or []
    ]


def fetch_key_stats(
    session: Optional[requests.Session] = None, timeout: float = 180
) -> List[InstrumentStatistic]:
    """GET and parse KEY_STATS_URL (about 28 MB)."""
    return parse_key_stats(
        get_json(tse_settings.KEY_STATS_URL, session=session, timeout=timeout)
    )
