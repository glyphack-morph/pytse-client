"""Prices of instruments: today's prices, the daily history of one
instrument and the recent daily prices of every instrument.

tse_settings constants and the pages that call them:

- TSE_CLOSING_PRICE_INFO_URL, ClosingPrice/GetClosingPriceInfo/{insCode}:
  instInfo, tab "در یک نگاه", the price box (آخرین معامله, قیمت پایانی,
  ...), polled every 4 to 5 seconds.
- TSE_TICKER_EXPORT_DATA_ADDRESS,
  ClosingPrice/GetClosingPriceDailyList/{insCode}/0: instInfo, tab
  "سابقه" (history).
- TSE_TICKER_RECENT_DAYS_URL,
  ClosingPrice/GetClosingPriceDailyList/{insCode}/12: instInfo, tab
  "در یک نگاه", box "سابقه معاملات" (last 12 days).
- CLOSING_PRICE_DAILY_ALL_INST_URL, ClosingPrice/GetClosingPriceDailyAllInst:
  market watch, toolbar "تنظیمات دیده بان" > "اطلاعات تکمیلی" > button
  "تاریخچه قیمت ها".

GetMarketWatch and GetIndexCompany also start with ClosingPrice/, they are
in market.py and index.py.

Prices and values are in rial, volumes in shares.
"""

import datetime
from dataclasses import dataclass
from typing import Any, List, Optional

import requests
from pytse_client import tse_settings
from pytse_client.tsetmc_api._convert import (
    to_date,
    to_optional_bool,
    to_optional_date,
    to_optional_float,
    to_optional_int,
    to_optional_time,
)
from pytse_client.utils.request_session import get_json

# ---------------------------------------------------------------------------
# ClosingPrice/GetClosingPriceInfo/{insCode} (TSE_CLOSING_PRICE_INFO_URL)


@dataclass(frozen=True, slots=True)
class InstrumentState:
    """State of an instrument (وضعیت), key instrumentState."""

    # cEtaval: state code, two letters padded with a space: "A " مجاز,
    # "I " ممنوع, "AS" مجاز-متوقف, "IS" ممنوع-متوقف, ...
    code: Optional[str]
    # cEtavalTitle: وضعیت, e.g. "مجاز"
    title: Optional[str]
    # idn: 0 in every answer seen
    idn: Optional[int] = None
    # dEven: 0 (no date) in every answer seen
    date: Optional[datetime.date] = None
    # hEven: 0 in every answer seen
    time: Optional[datetime.time] = None
    # insCode: null in every answer seen
    ins_code: Optional[str] = None
    # lVal18AFC: null in every answer seen
    symbol: Optional[str] = None
    # lVal30: null in every answer seen
    name: Optional[str] = None
    # realHeven: 0 in every answer seen
    real_time: Optional[datetime.time] = None
    # underSupervision: 1 when the symbol is under supervision (مشمول
    # فرآیند نظارتی)
    under_supervision: Optional[int] = None


@dataclass(frozen=True, slots=True)
class ClosingPriceInfo:
    """Today's prices of an instrument (key closingPriceInfo).

    Prices can be None, the library treats real time data as optional.
    """

    # instrumentState: وضعیت of the instrument
    instrument_state: Optional[InstrumentState]
    # pDrCotVal: آخرین معامله (last trade price)
    last_price: Optional[int]
    # pClosing: قیمت پایانی (closing price)
    closing_price: Optional[int]
    # priceYesterday: قیمت دیروز
    yesterday_price: Optional[int]
    # priceFirst: اولین قیمت
    first_price: Optional[int]
    # priceMax: high of بازه روز
    high_price: Optional[int]
    # priceMin: low of بازه روز
    low_price: Optional[int]
    # zTotTran: تعداد معاملات
    trade_count: Optional[int]
    # qTotTran5J: حجم معاملات, shares
    volume: Optional[int]
    # qTotCap: ارزش معاملات, rial
    value: Optional[int]
    # dEven: day of the prices, None (0) when there is none
    date: Optional[datetime.date]
    # hEven: time of the prices
    time: Optional[datetime.time]
    # lastHEven: time of "آخرین اطلاعات قیمت"
    last_time: Optional[datetime.time] = None
    # finalLastDate: last trading day of the instrument, shown in
    # "آخرین اطلاعات قیمت" when lastHEven is 0
    last_date: Optional[datetime.date] = None
    # nvt: ارزش مفهومی (notional value) of options, rial
    notional_value: Optional[int] = None
    # mop: موقعیت باز (open positions) of options and futures
    open_positions: Optional[int] = None
    # pRedTran: 0 in every answer seen, the NAV of funds comes from
    # Fund/GetETFByInsCode
    nav: Optional[int] = None
    # priceChange: 0 in every answer seen
    price_change: Optional[float] = None
    # last: true in every answer seen
    last: Optional[bool] = None
    # id: 0 in every answer seen
    id: Optional[int] = None
    # insCode: "0" in every answer seen
    ins_code: Optional[str] = None
    # iClose: false in every answer seen
    i_close: Optional[bool] = None
    # yClose: false in every answer seen
    y_close: Optional[bool] = None
    # instrument: null in every answer seen
    instrument: Optional[Any] = None
    # thirtyDayClosingHistory: null in every answer seen
    thirty_day_closing_history: Optional[Any] = None


def _parse_instrument_state(state: Any) -> InstrumentState:
    return InstrumentState(
        code=state["cEtaval"],
        title=state["cEtavalTitle"],
        idn=state.get("idn"),
        date=to_optional_date(state.get("dEven")),
        time=to_optional_time(state.get("hEven")),
        ins_code=state.get("insCode"),
        symbol=state.get("lVal18AFC"),
        name=state.get("lVal30"),
        real_time=to_optional_time(state.get("realHeven")),
        under_supervision=state.get("underSupervision"),
    )


def parse_closing_price_info(data: Any) -> Optional[ClosingPriceInfo]:
    """Parse the JSON of ClosingPrice/GetClosingPriceInfo/{insCode}, None
    when the API sends no prices."""
    info = data["closingPriceInfo"]
    if not info:
        return None
    state = info["instrumentState"]
    return ClosingPriceInfo(
        instrument_state=_parse_instrument_state(state) if state else None,
        last_price=to_optional_int(info["pDrCotVal"]),
        closing_price=to_optional_int(info["pClosing"]),
        yesterday_price=to_optional_int(info["priceYesterday"]),
        first_price=to_optional_int(info["priceFirst"]),
        high_price=to_optional_int(info["priceMax"]),
        low_price=to_optional_int(info["priceMin"]),
        trade_count=to_optional_int(info["zTotTran"]),
        volume=to_optional_int(info["qTotTran5J"]),
        value=to_optional_int(info["qTotCap"]),
        date=to_optional_date(info["dEven"]),
        time=to_optional_time(info["hEven"]),
        last_time=to_optional_time(info.get("lastHEven")),
        last_date=to_optional_date(info.get("finalLastDate")),
        notional_value=to_optional_int(info.get("nvt")),
        open_positions=to_optional_int(info.get("mop")),
        nav=to_optional_int(info.get("pRedTran")),
        price_change=to_optional_float(info.get("priceChange")),
        last=to_optional_bool(info.get("last")),
        id=info.get("id"),
        ins_code=info.get("insCode"),
        i_close=to_optional_bool(info.get("iClose")),
        y_close=to_optional_bool(info.get("yClose")),
        instrument=info.get("instrument"),
        thirty_day_closing_history=info.get("thirtyDayClosingHistory"),
    )


def fetch_closing_price_info(
    ins_code: str,
    session: Optional[requests.Session] = None,
    timeout: float = 30,
) -> Optional[ClosingPriceInfo]:
    """GET and parse TSE_CLOSING_PRICE_INFO_URL of an instrument."""
    return parse_closing_price_info(
        get_json(
            tse_settings.TSE_CLOSING_PRICE_INFO_URL.format(ins_code),
            session=session,
            timeout=timeout,
        )
    )


# ---------------------------------------------------------------------------
# ClosingPrice/GetClosingPriceDailyList/{insCode}/0
# (TSE_TICKER_EXPORT_DATA_ADDRESS)


@dataclass(frozen=True, slots=True)
class ClosingPriceDaily:
    """One day of the price history of an instrument (key
    closingPriceDaily), a row of tab "سابقه"."""

    # dEven: تاریخ
    date: datetime.date
    # priceFirst: اولین قیمت
    first_price: int
    # priceMax: بیشترین
    high_price: int
    # priceMin: کمترین
    low_price: int
    # pClosing: قیمت پایانی (closing price)
    closing_price: int
    # pDrCotVal: آخرین معامله (last trade price)
    last_price: int
    # priceYesterday: قیمت دیروز
    yesterday_price: int
    # zTotTran: تعداد (number of trades), 0 on days without a trade
    trade_count: int
    # qTotTran5J: حجم (volume), shares
    volume: int
    # qTotCap: ارزش (value), rial
    value: int
    # priceChange: change of the closing price since the previous day
    price_change: Optional[float] = None
    # hEven: time of the last price of the day
    time: Optional[datetime.time] = None
    # insCode: instrument code
    ins_code: Optional[str] = None
    # last: true for the newest day
    last: Optional[bool] = None
    # id: 0 in every row seen
    id: Optional[int] = None
    # iClose: meaning unknown, not shown on the website
    i_close: Optional[bool] = None
    # yClose: meaning unknown, not shown on the website
    y_close: Optional[bool] = None


def parse_closing_price_daily_list(data: Any) -> List[ClosingPriceDaily]:
    """Parse the JSON of ClosingPrice/GetClosingPriceDailyList, newest
    day first (thousands of rows)."""
    return [
        ClosingPriceDaily(
            date=to_date(row["dEven"]),
            first_price=int(row["priceFirst"]),
            high_price=int(row["priceMax"]),
            low_price=int(row["priceMin"]),
            closing_price=int(row["pClosing"]),
            last_price=int(row["pDrCotVal"]),
            yesterday_price=int(row["priceYesterday"]),
            trade_count=int(row["zTotTran"]),
            volume=int(row["qTotTran5J"]),
            value=int(row["qTotCap"]),
            price_change=to_optional_float(row.get("priceChange")),
            time=to_optional_time(row.get("hEven")),
            ins_code=row.get("insCode"),
            last=to_optional_bool(row.get("last")),
            id=row.get("id"),
            i_close=to_optional_bool(row.get("iClose")),
            y_close=to_optional_bool(row.get("yClose")),
        )
        for row in data["closingPriceDaily"] or []
    ]


def fetch_closing_price_daily_list(
    ins_code: str,
    session: Optional[requests.Session] = None,
    timeout: float = 60,
) -> List[ClosingPriceDaily]:
    """GET and parse TSE_TICKER_EXPORT_DATA_ADDRESS of an instrument."""
    return parse_closing_price_daily_list(
        get_json(
            tse_settings.TSE_TICKER_EXPORT_DATA_ADDRESS.format(ins_code),
            session=session,
            timeout=timeout,
        )
    )


def fetch_recent_closing_price_daily_list(
    ins_code: str,
    session: Optional[requests.Session] = None,
    timeout: float = 30,
) -> List[ClosingPriceDaily]:
    """GET and parse TSE_TICKER_RECENT_DAYS_URL (the last 12 days) of an
    instrument. Same response as TSE_TICKER_EXPORT_DATA_ADDRESS."""
    return parse_closing_price_daily_list(
        get_json(
            tse_settings.TSE_TICKER_RECENT_DAYS_URL.format(ins_code),
            session=session,
            timeout=timeout,
        )
    )


# ---------------------------------------------------------------------------
# ClosingPrice/GetClosingPriceDailyAllInst (CLOSING_PRICE_DAILY_ALL_INST_URL)


@dataclass(frozen=True, slots=True)
class ClosingPriceDailyAllInst:
    """One day of one instrument in the daily prices of every instrument
    for the last ~60 trading days (key closingPriceDailyAllInst). It also
    has suspended instruments that the market watch leaves out."""

    # insCode: instrument code
    ins_code: str
    # dEven: day
    date: Optional[datetime.date] = None
    # hEven: 0 in every row seen
    time: Optional[datetime.time] = None
    # priceFirst: اولین قیمت
    first_price: Optional[int] = None
    # priceMax: بیشترین
    high_price: Optional[int] = None
    # priceMin: کمترین
    low_price: Optional[int] = None
    # pClosing: قیمت پایانی
    closing_price: Optional[int] = None
    # pDrCotVal: آخرین معامله
    last_price: Optional[int] = None
    # priceYesterday: قیمت دیروز
    yesterday_price: Optional[int] = None
    # zTotTran: تعداد معاملات
    trade_count: Optional[int] = None
    # qTotTran5J: حجم معاملات, shares
    volume: Optional[int] = None
    # qTotCap: ارزش معاملات, rial
    value: Optional[int] = None
    # offset: 0 in every row seen
    offset: Optional[int] = None
    # id: 0 in every row seen
    id: Optional[int] = None
    # iClose: meaning unknown, not shown on the website
    i_close: Optional[bool] = None
    # yClose: meaning unknown, not shown on the website
    y_close: Optional[bool] = None


def parse_closing_price_daily_all_inst(
    data: Any,
) -> List[ClosingPriceDailyAllInst]:
    """Parse the JSON of ClosingPrice/GetClosingPriceDailyAllInst (about
    200k rows)."""
    return [
        ClosingPriceDailyAllInst(
            ins_code=row["insCode"],
            date=to_optional_date(row.get("dEven")),
            time=to_optional_time(row.get("hEven")),
            first_price=to_optional_int(row.get("priceFirst")),
            high_price=to_optional_int(row.get("priceMax")),
            low_price=to_optional_int(row.get("priceMin")),
            closing_price=to_optional_int(row.get("pClosing")),
            last_price=to_optional_int(row.get("pDrCotVal")),
            yesterday_price=to_optional_int(row.get("priceYesterday")),
            trade_count=to_optional_int(row.get("zTotTran")),
            volume=to_optional_int(row.get("qTotTran5J")),
            value=to_optional_int(row.get("qTotCap")),
            offset=row.get("offset"),
            id=row.get("id"),
            i_close=to_optional_bool(row.get("iClose")),
            y_close=to_optional_bool(row.get("yClose")),
        )
        for row in data["closingPriceDailyAllInst"] or []
    ]


def fetch_closing_price_daily_all_inst(
    session: Optional[requests.Session] = None, timeout: float = 300
) -> List[ClosingPriceDailyAllInst]:
    """GET and parse CLOSING_PRICE_DAILY_ALL_INST_URL (about 55 MB)."""
    return parse_closing_price_daily_all_inst(
        get_json(
            tse_settings.CLOSING_PRICE_DAILY_ALL_INST_URL,
            session=session,
            timeout=timeout,
        )
    )
