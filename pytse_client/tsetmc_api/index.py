"""Financial indices (شاخص): daily history, today's values, the last value
of every index and the companies in an index.

tse_settings constants and the pages that call them:

- TSE_FINANCIAL_INDEX_EXPORT_DATA_ADDRESS, Index/GetIndexB2History/{insCode}:
  IndexInfo, section "سابقه شاخص".
- FINANCIAL_INDEX_EXPORT_INTRADAY_URL, Index/GetIndexB1LastDay/{insCode}:
  IndexInfo, section "سابقه شاخص روز جاری".
- INDICES_LIST_URL, Index/GetIndexB1LastAll/All/{flow}: home page, tab
  "در یک نگاه", the "شاخص های منتخب" header of the بورس (flow 1) or
  فرابورس (flow 2) box.
- FINANCIAL_INDEX_COMPANIES_URL, ClosingPrice/GetIndexCompany/{insCode}:
  IndexInfo, section "شرکت های موجود در شاخص".

Prices and values are in rial, volumes in shares.
"""

import datetime
from dataclasses import dataclass, field
from typing import Any, List, Optional

import requests
from pytse_client import tse_settings
from pytse_client.tsetmc_api._convert import (
    to_date,
    to_optional_bool,
    to_optional_date,
    to_optional_float,
    to_optional_int,
    to_optional_str,
    to_optional_time,
    to_time,
)
from pytse_client.utils.request_session import get_json

# ---------------------------------------------------------------------------
# Index/GetIndexB2History/{insCode} (TSE_FINANCIAL_INDEX_EXPORT_DATA_ADDRESS)


@dataclass(frozen=True, slots=True)
class IndexHistory:
    """One day of an index (key indexB2), a row of "سابقه شاخص"."""

    # dEven: تاریخ
    date: datetime.date
    # xNivInuClMresIbs: مقدار شاخص (value at the close)
    close: float
    # xNivInuPbMresIbs: کمترین (low of the day)
    low: float
    # xNivInuPhMresIbs: بیشترین (high of the day)
    high: float
    # insCode: index code, sent as a number by this endpoint
    ins_code: Optional[str] = None


def parse_index_history(data: Any) -> List[IndexHistory]:
    """Parse the JSON of Index/GetIndexB2History/{insCode}, oldest day
    first (thousands of rows)."""
    return [
        IndexHistory(
            date=to_date(row["dEven"]),
            close=float(row["xNivInuClMresIbs"]),
            low=float(row["xNivInuPbMresIbs"]),
            high=float(row["xNivInuPhMresIbs"]),
            ins_code=to_optional_str(row.get("insCode")),
        )
        for row in data.get("indexB2") or []
    ]


def fetch_index_history(
    ins_code: str,
    session: Optional[requests.Session] = None,
    timeout: float = 60,
) -> List[IndexHistory]:
    """GET and parse TSE_FINANCIAL_INDEX_EXPORT_DATA_ADDRESS of an index."""
    return parse_index_history(
        get_json(
            tse_settings.TSE_FINANCIAL_INDEX_EXPORT_DATA_ADDRESS.format(
                ins_code
            ),
            session=session,
            timeout=timeout,
        )
    )


# ---------------------------------------------------------------------------
# Index/GetIndexB1LastDay/{insCode} (FINANCIAL_INDEX_EXPORT_INTRADAY_URL)


@dataclass(frozen=True, slots=True)
class IndexIntraday:
    """One value of an index on the last trading day (key indexB1), a row
    of "سابقه شاخص روز جاری"."""

    # hEven: زمان انتشار (publish time)
    time: datetime.time
    # xDrNivJIdx004: مقدار (value)
    value: float
    # xVarIdxJRfV: درصد تغییر, change since the previous day, percent
    change_percent: float
    # xPbNivJIdx004: کمترین (low of the day so far), 0 before the open
    low: float
    # xPhNivJIdx004: بیشترین (high of the day so far), 0 before the open
    high: float
    # dEven: day
    date: Optional[datetime.date] = None
    # indexChange: 0 in every row seen
    change: Optional[float] = None
    # last: true for the newest row
    last: Optional[bool] = None
    # insCode: null in every row seen
    ins_code: Optional[str] = None
    # lVal30: null in every row seen
    name: Optional[str] = None
    # c1: 0 in every row seen, meaning unknown
    c1: Optional[int] = None
    # c2: 0 in every row seen, meaning unknown
    c2: Optional[int] = None
    # c3: 0 in every row seen, meaning unknown
    c3: Optional[int] = None
    # c4: 0 in every row seen, meaning unknown
    c4: Optional[int] = None


def parse_index_intraday(data: Any) -> List[IndexIntraday]:
    """Parse the JSON of Index/GetIndexB1LastDay/{insCode}, in the order of
    the API."""
    return [
        IndexIntraday(
            time=to_time(row["hEven"]),
            value=float(row["xDrNivJIdx004"]),
            change_percent=float(row["xVarIdxJRfV"]),
            low=float(row["xPbNivJIdx004"]),
            high=float(row["xPhNivJIdx004"]),
            date=to_optional_date(row.get("dEven")),
            change=to_optional_float(row.get("indexChange")),
            last=to_optional_bool(row.get("last")),
            ins_code=to_optional_str(row.get("insCode")),
            name=row.get("lVal30"),
            c1=row.get("c1"),
            c2=row.get("c2"),
            c3=row.get("c3"),
            c4=row.get("c4"),
        )
        for row in data["indexB1"] or []
    ]


def fetch_index_intraday(
    ins_code: str,
    session: Optional[requests.Session] = None,
    timeout: float = 30,
) -> List[IndexIntraday]:
    """GET and parse FINANCIAL_INDEX_EXPORT_INTRADAY_URL of an index."""
    return parse_index_intraday(
        get_json(
            tse_settings.FINANCIAL_INDEX_EXPORT_INTRADAY_URL.format(ins_code),
            session=session,
            timeout=timeout,
        )
    )


# ---------------------------------------------------------------------------
# Index/GetIndexB1LastAll/All/{flow} (INDICES_LIST_URL)


@dataclass(frozen=True, slots=True)
class IndexLastValue:
    """Last value of one index of a market (key indexB1), a row of the
    "شاخص های منتخب" window."""

    # insCode: index code
    ins_code: str
    # lVal30: شاخص (title), sometimes with the section number, e.g.
    # "27-فلزات اساسي" or "بيمه و بازنشسته66"; Arabic ي and ك
    name: str
    # hEven: انتشار (publish time)
    time: Optional[datetime.time] = None
    # xDrNivJIdx004: مقدار (value)
    value: Optional[float] = None
    # indexChange: تغییر (change since the previous day)
    change: Optional[float] = None
    # xVarIdxJRfV: درصد (change since the previous day, percent)
    change_percent: Optional[float] = None
    # xPhNivJIdx004: بیشترین (high of the day)
    high: Optional[float] = None
    # xPbNivJIdx004: کمترین (low of the day)
    low: Optional[float] = None
    # dEven: 0 (no date) in every row seen
    date: Optional[datetime.date] = None
    # last: false in every row seen
    last: Optional[bool] = None
    # c1: 0 in every row seen, meaning unknown
    c1: Optional[int] = None
    # c2: 0 in every row seen, meaning unknown
    c2: Optional[int] = None
    # c3: 0 in every row seen, meaning unknown
    c3: Optional[int] = None
    # c4: 0 in every row seen, meaning unknown
    c4: Optional[int] = None


def parse_indices(data: Any) -> List[IndexLastValue]:
    """Parse the JSON of Index/GetIndexB1LastAll/All/{flow}."""
    return [
        IndexLastValue(
            ins_code=str(row["insCode"]),
            name=row["lVal30"],
            time=to_optional_time(row.get("hEven")),
            value=to_optional_float(row.get("xDrNivJIdx004")),
            change=to_optional_float(row.get("indexChange")),
            change_percent=to_optional_float(row.get("xVarIdxJRfV")),
            high=to_optional_float(row.get("xPhNivJIdx004")),
            low=to_optional_float(row.get("xPbNivJIdx004")),
            date=to_optional_date(row.get("dEven")),
            last=to_optional_bool(row.get("last")),
            c1=row.get("c1"),
            c2=row.get("c2"),
            c3=row.get("c3"),
            c4=row.get("c4"),
        )
        for row in data["indexB1"] or []
    ]


def fetch_indices(
    flow: int,
    session: Optional[requests.Session] = None,
    timeout: float = 30,
) -> List[IndexLastValue]:
    """GET and parse INDICES_LIST_URL of a flow (1 بورس, 2 فرابورس)."""
    return parse_indices(
        get_json(
            tse_settings.INDICES_LIST_URL.format(flow),
            session=session,
            timeout=timeout,
        )
    )


# ---------------------------------------------------------------------------
# ClosingPrice/GetIndexCompany/{insCode} (FINANCIAL_INDEX_COMPANIES_URL)


@dataclass(frozen=True, slots=True)
class IndexCompanyInstrument:
    """The company of a row of GetIndexCompany (key instrument); only the
    code, symbol and name are filled, the rest is null or 0."""

    # lVal18AFC: نماد (symbol), Arabic ي and ك
    symbol: str
    # lVal30: name of the company, Arabic ي and ك
    name: Optional[str] = None
    # insCode: instrument code
    ins_code: Optional[str] = None
    # cValMne: null in every row seen
    c_val_mne: Optional[str] = None
    # lVal18: null in every row seen (the Latin name elsewhere)
    latin_name: Optional[str] = None
    # cSocCSAC: null in every row seen
    c_soc_csac: Optional[str] = None
    # lSoc30: null in every row seen
    l_soc30: Optional[str] = None
    # yMarNSC: null in every row seen (market code elsewhere)
    market_code: Optional[str] = None
    # yVal: null in every row seen (instrument type elsewhere)
    instrument_type: Optional[str] = None
    # flow: 0 in every row seen
    flow: Optional[int] = None
    # cIsin: null in every row seen (ISIN of the company elsewhere)
    company_isin: Optional[str] = None
    # zTitad: 0 in every row seen (total shares elsewhere)
    total_shares: Optional[int] = None
    # baseVol: 0 in every row seen (base volume elsewhere)
    base_volume: Optional[int] = None
    # instrumentID: null in every row seen (ISIN of the symbol elsewhere)
    isin: Optional[str] = None
    # cgrValCot: null in every row seen (board code elsewhere)
    board_code: Optional[str] = None
    # cComVal: null in every row seen
    c_com_val: Optional[str] = None
    # lastDate: 0 in every row seen
    last_date: Optional[int] = None
    # sourceID: 0 in every row seen
    source_id: Optional[int] = None
    # flowTitle: null in every row seen
    flow_title: Optional[str] = None
    # cgrValCotTitle: null in every row seen
    board_title: Optional[str] = None


@dataclass(frozen=True, slots=True)
class IndexCompany:
    """One company of an index with its prices of the last trading day (a
    row of key indexCompany), a row of "شرکت های موجود در شاخص"."""

    # insCode: instrument code of the company
    ins_code: str
    # instrument: symbol and name of the company
    instrument: IndexCompanyInstrument
    # pClosing: قیمت پایانی
    closing_price: Optional[int] = None
    # priceChange: تغییر of the closing price
    price_change: Optional[float] = None
    # pDrCotVal: آخرین معامله
    last_price: Optional[int] = None
    # priceFirst: اولین قیمت
    first_price: Optional[int] = None
    # priceYesterday: قیمت دیروز
    yesterday_price: Optional[int] = None
    # priceMax: بیشترین
    high_price: Optional[int] = None
    # priceMin: کمترین
    low_price: Optional[int] = None
    # zTotTran: تعداد معاملات
    trade_count: Optional[int] = None
    # qTotTran5J: حجم معاملات, shares
    volume: Optional[int] = None
    # qTotCap: ارزش معاملات, rial
    value: Optional[int] = None
    # instrumentState: null in every row seen
    instrument_state: Optional[Any] = None
    # lastHEven: 0 in every row seen
    last_time: Optional[datetime.time] = None
    # finalLastDate: 0 (no date) in every row seen
    last_date: Optional[datetime.date] = None
    # nvt: 0 in every row seen
    notional_value: Optional[int] = None
    # mop: 0 in every row seen
    open_positions: Optional[int] = None
    # pRedTran: 0 in every row seen
    nav: Optional[int] = None
    # thirtyDayClosingHistory: null in every row seen, see
    # IndexCompanies.thirty_day_history
    thirty_day_closing_history: Optional[Any] = None
    # last: false in every row seen
    last: Optional[bool] = None
    # id: 0 in every row seen
    id: Optional[int] = None
    # dEven: 0 (no date) in every row seen
    date: Optional[datetime.date] = None
    # hEven: 0 in every row seen
    time: Optional[datetime.time] = None
    # iClose: false in every row seen
    i_close: Optional[bool] = None
    # yClose: false in every row seen
    y_close: Optional[bool] = None


@dataclass(frozen=True, slots=True)
class IndexCompanyClosingPrice:
    """One day of the last 30 days of a company of the index (a row of key
    relatedCompanyThirtyDayHistory)."""

    # insCode: instrument code of the company
    ins_code: Optional[str] = None
    # dEven: day
    date: Optional[datetime.date] = None
    # pClosing: قیمت پایانی
    closing_price: Optional[int] = None
    # pDrCotVal: 0 in every row seen
    last_price: Optional[int] = None
    # zTotTran: 0 in every row seen
    trade_count: Optional[int] = None
    # qTotTran5J: 0 in every row seen
    volume: Optional[int] = None
    # qTotCap: 0 in every row seen
    value: Optional[int] = None
    # hEven: 0 in every row seen
    time: Optional[datetime.time] = None
    # id: 0 in every row seen
    id: Optional[int] = None
    # iClose: false in every row seen
    i_close: Optional[bool] = None
    # yClose: false in every row seen
    y_close: Optional[bool] = None


@dataclass(frozen=True, slots=True)
class IndexCompanies:
    """Response of ClosingPrice/GetIndexCompany/{insCode}."""

    # indexCompany: the companies of the index
    companies: List[IndexCompany]
    # relatedCompanyThirtyDayHistory: closing prices of the companies in
    # the last 30 days
    thirty_day_history: List[IndexCompanyClosingPrice] = field(
        default_factory=list
    )


def _parse_index_company_instrument(row: Any) -> IndexCompanyInstrument:
    return IndexCompanyInstrument(
        symbol=row["lVal18AFC"],
        name=row.get("lVal30"),
        ins_code=to_optional_str(row.get("insCode")),
        c_val_mne=row.get("cValMne"),
        latin_name=row.get("lVal18"),
        c_soc_csac=row.get("cSocCSAC"),
        l_soc30=row.get("lSoc30"),
        market_code=row.get("yMarNSC"),
        instrument_type=to_optional_str(row.get("yVal")),
        flow=row.get("flow"),
        company_isin=row.get("cIsin"),
        total_shares=to_optional_int(row.get("zTitad")),
        base_volume=to_optional_int(row.get("baseVol")),
        isin=row.get("instrumentID"),
        board_code=row.get("cgrValCot"),
        c_com_val=row.get("cComVal"),
        last_date=row.get("lastDate"),
        source_id=row.get("sourceID"),
        flow_title=row.get("flowTitle"),
        board_title=row.get("cgrValCotTitle"),
    )


def _parse_index_company(row: Any) -> IndexCompany:
    return IndexCompany(
        ins_code=str(row["insCode"]),
        instrument=_parse_index_company_instrument(row["instrument"]),
        closing_price=to_optional_int(row.get("pClosing")),
        price_change=to_optional_float(row.get("priceChange")),
        last_price=to_optional_int(row.get("pDrCotVal")),
        first_price=to_optional_int(row.get("priceFirst")),
        yesterday_price=to_optional_int(row.get("priceYesterday")),
        high_price=to_optional_int(row.get("priceMax")),
        low_price=to_optional_int(row.get("priceMin")),
        trade_count=to_optional_int(row.get("zTotTran")),
        volume=to_optional_int(row.get("qTotTran5J")),
        value=to_optional_int(row.get("qTotCap")),
        instrument_state=row.get("instrumentState"),
        last_time=to_optional_time(row.get("lastHEven")),
        last_date=to_optional_date(row.get("finalLastDate")),
        notional_value=to_optional_int(row.get("nvt")),
        open_positions=to_optional_int(row.get("mop")),
        nav=to_optional_int(row.get("pRedTran")),
        thirty_day_closing_history=row.get("thirtyDayClosingHistory"),
        last=to_optional_bool(row.get("last")),
        id=row.get("id"),
        date=to_optional_date(row.get("dEven")),
        time=to_optional_time(row.get("hEven")),
        i_close=to_optional_bool(row.get("iClose")),
        y_close=to_optional_bool(row.get("yClose")),
    )


def _parse_index_company_closing_price(row: Any) -> IndexCompanyClosingPrice:
    return IndexCompanyClosingPrice(
        ins_code=to_optional_str(row.get("insCode")),
        date=to_optional_date(row.get("dEven")),
        closing_price=to_optional_int(row.get("pClosing")),
        last_price=to_optional_int(row.get("pDrCotVal")),
        trade_count=to_optional_int(row.get("zTotTran")),
        volume=to_optional_int(row.get("qTotTran5J")),
        value=to_optional_int(row.get("qTotCap")),
        time=to_optional_time(row.get("hEven")),
        id=row.get("id"),
        i_close=to_optional_bool(row.get("iClose")),
        y_close=to_optional_bool(row.get("yClose")),
    )


def parse_index_companies(data: Any) -> IndexCompanies:
    """Parse the JSON of ClosingPrice/GetIndexCompany/{insCode}."""
    return IndexCompanies(
        companies=[
            _parse_index_company(row) for row in data["indexCompany"] or []
        ],
        thirty_day_history=[
            _parse_index_company_closing_price(row)
            for row in data.get("relatedCompanyThirtyDayHistory") or []
        ],
    )


def fetch_index_companies(
    ins_code: str,
    session: Optional[requests.Session] = None,
    timeout: float = 60,
) -> IndexCompanies:
    """GET and parse FINANCIAL_INDEX_COMPANIES_URL of an index."""
    return parse_index_companies(
        get_json(
            tse_settings.FINANCIAL_INDEX_COMPANIES_URL.format(ins_code),
            session=session,
            timeout=timeout,
        )
    )
