"""Instrument (نماد) information: the page header of a symbol, the symbol
search and the information of a symbol on a past day.

tse_settings constants and the pages that call them:

- TSE_INSTRUMENT_INFO, Instrument/GetInstrumentInfo/{insCode}: instInfo,
  loaded with the page (title, EPS and P/E box, تعداد سهام, حجم مبنا,
  سهام شناور, میانگین حجم ماه, گروه of tab "در یک نگاه").
- TSE_SYMBOL_ID_URL, Instrument/GetInstrumentSearch/{text}: any page, top
  bar icon "جستجو" (search), sent on every key press.
- SYMBOL_DAY_INSTRUMENT_INFO_URL,
  Instrument/GetInstrumentHistory/{insCode}/{date}: History page, loaded
  with the page (its header).

Names and symbols use the Arabic ي and ك of the website. Prices are in
rial, volumes in shares.
"""

import datetime
from dataclasses import dataclass
from typing import Any, List, Optional
from urllib.parse import quote

import requests
from pytse_client import tse_settings
from pytse_client.tsetmc_api._convert import (
    number_text_to_float,
    to_optional_date,
    to_optional_float,
    to_optional_int,
    to_optional_str,
    to_optional_time,
)
from pytse_client.utils.request_session import get_json

# ---------------------------------------------------------------------------
# Instrument/GetInstrumentInfo/{insCode} (TSE_INSTRUMENT_INFO)


@dataclass(frozen=True, slots=True)
class InstrumentEps:
    """EPS line of tab "در یک نگاه" (key eps)."""

    # estimatedEPS: EPS (مقدار سود هر سهم), rial, sent as text; None
    # when the instrument has none (funds, indices, ...)
    estimated_eps: Optional[float]
    # sectorPE: P/E گروه (P/E of the sector)
    sector_pe: Optional[float]
    # psr: PSR (price to sales ratio of a share), rial
    psr: Optional[float]
    # epsValue: null in every answer seen
    eps_value: Optional[float] = None


@dataclass(frozen=True, slots=True)
class InstrumentSector:
    """Sector (گروه) of an instrument (key sector)."""

    # lSecVal: گروه, sector name, e.g. "فلزات اساسي"
    name: Optional[str]
    # cSecVal: sector code padded with a space, e.g. "27 "
    code: Optional[str] = None
    # dEven: 0 (no date) in every answer seen
    date: Optional[datetime.date] = None


@dataclass(frozen=True, slots=True)
class StaticThreshold:
    """قیمت مجاز (allowed price range of the day), key staticThreshold."""

    # psGelStaMax: upper limit of قیمت مجاز, rial
    max_price: Optional[int]
    # psGelStaMin: lower limit of قیمت مجاز, rial
    min_price: Optional[int]
    # insCode: null in every answer seen
    ins_code: Optional[str] = None
    # dEven: 0 (no date) in every answer seen
    date: Optional[datetime.date] = None
    # hEven: 0 in every answer seen
    time: Optional[datetime.time] = None


@dataclass(frozen=True, slots=True)
class InstrumentInfo:
    """Information of an instrument (key instrumentInfo).

    Numbers the library reads are Optional because they are null for some
    kinds of instruments; Ticker turns that into None.
    """

    # eps: EPS line
    eps: InstrumentEps
    # sector: گروه
    sector: InstrumentSector
    # staticThreshold: قیمت مجاز, None when the API sends null
    static_threshold: Optional[StaticThreshold]
    # minWeek: low of بازه هفته (last week), rial
    min_week: Optional[int]
    # maxWeek: high of بازه هفته, rial
    max_week: Optional[int]
    # minYear: low of بازه سال (last year), rial
    min_year: Optional[int]
    # maxYear: high of بازه سال, rial
    max_year: Optional[int]
    # qTotTran5JAvg: میانگین حجم ماه (average daily volume of the last
    # month), shares
    month_average_volume: Optional[int]
    # kAjCapValCpsIdx: سهام شناور (free float), percent, sent as text;
    # None when empty
    free_float: Optional[float]
    # lVal18AFC: نماد فارسی (symbol), e.g. "فولاد"
    symbol: str
    # lVal30: نام (name and title of the page), e.g. "فولاد مباركه اصفهان"
    name: str
    # flow: market, 1 بورس, 2 فرابورس, 3 آتی, 4 پایه فرابورس, ...
    flow: Optional[int]
    # instrumentID: کد 12 رقمی نماد (ISIN of the symbol), e.g.
    # "IRO1FOLD0001"
    isin: Optional[str]
    # cIsin: کد 12 رقمی شرکت (ISIN of the company), e.g. "IRO1FOLD0009"
    company_isin: Optional[str]
    # zTitad: تعداد سهام (total shares)
    total_shares: Optional[int]
    # baseVol: حجم مبنا (base volume), shares
    base_volume: Optional[int]
    # insCode: instrument code
    ins_code: Optional[str] = None
    # flowTitle: بازار, e.g. "بازار بورس"
    flow_title: Optional[str] = None
    # lVal18: نام لاتین (Latin name), e.g. "S*Mobarakeh Steel"
    latin_name: Optional[str] = None
    # cgrValCot: board code, e.g. "N1"
    board_code: Optional[str] = None
    # cgrValCotTitle: board, e.g. "بازار اول (تابلوی اصلی) بورس"
    board_title: Optional[str] = None
    # cComVal: کد تابلو, e.g. "1"
    c_com_val: Optional[str] = None
    # yVal: instrument type code, e.g. "300" for a share
    instrument_type: Optional[str] = None
    # nav: 0 in every answer seen, the NAV of funds comes from
    # Fund/GetETFByInsCode
    nav: Optional[float] = None
    # contractSize: اندازه قرارداد of options and futures
    contract_size: Optional[int] = None
    # etfIssuedUnit: تعداد واحدهای صادر شده (issued units) of funds
    etf_issued_units: Optional[int] = None
    # etfUnitDeven: day of etfIssuedUnit
    etf_unit_date: Optional[datetime.date] = None
    # faraDesc: text shown under the title, e.g. "نوع صندوق : سهامی"
    fara_desc: Optional[str] = None
    # underSupervision: 1 when the symbol is under supervision (مشمول
    # فرآیند نظارتی)
    under_supervision: Optional[int] = None
    # topInst: 1 for the large companies, meaning not shown
    top_inst: Optional[int] = None
    # sourceID: 1 for بورس, 2 for فرابورس
    source_id: Optional[int] = None
    # lastDate: 0 in every answer seen
    last_date: Optional[int] = None
    # dEven: 0 (no date) in every answer seen
    date: Optional[datetime.date] = None
    # cValMne: کد 5 رقمی نماد, null in every answer seen
    c_val_mne: Optional[str] = None
    # cSocCSAC: کد 4 رقمی شرکت, null in every answer seen
    c_soc_csac: Optional[str] = None
    # lSoc30: نام شرکت, null in every answer seen
    l_soc30: Optional[str] = None
    # yMarNSC: market code, null in every answer seen
    market_code: Optional[str] = None


def parse_instrument_info(data: Any) -> InstrumentInfo:
    """Parse the JSON of Instrument/GetInstrumentInfo/{insCode}."""
    info = data["instrumentInfo"]
    eps = info["eps"]
    sector = info["sector"]
    threshold = info["staticThreshold"]
    return InstrumentInfo(
        eps=InstrumentEps(
            estimated_eps=number_text_to_float(eps["estimatedEPS"]),
            sector_pe=number_text_to_float(eps["sectorPE"]),
            psr=number_text_to_float(eps["psr"]),
            eps_value=to_optional_float(eps.get("epsValue")),
        ),
        sector=InstrumentSector(
            name=sector["lSecVal"],
            code=sector.get("cSecVal"),
            date=to_optional_date(sector.get("dEven")),
        ),
        static_threshold=(
            StaticThreshold(
                max_price=to_optional_int(threshold["psGelStaMax"]),
                min_price=to_optional_int(threshold["psGelStaMin"]),
                ins_code=threshold.get("insCode"),
                date=to_optional_date(threshold.get("dEven")),
                time=to_optional_time(threshold.get("hEven")),
            )
            if threshold
            else None
        ),
        min_week=to_optional_int(info["minWeek"]),
        max_week=to_optional_int(info["maxWeek"]),
        min_year=to_optional_int(info["minYear"]),
        max_year=to_optional_int(info["maxYear"]),
        month_average_volume=to_optional_int(info["qTotTran5JAvg"]),
        free_float=number_text_to_float(info["kAjCapValCpsIdx"]),
        symbol=info["lVal18AFC"],
        name=info["lVal30"],
        flow=to_optional_int(info["flow"]),
        isin=info["instrumentID"],
        company_isin=info["cIsin"],
        total_shares=to_optional_int(info["zTitad"]),
        base_volume=to_optional_int(info["baseVol"]),
        ins_code=to_optional_str(info.get("insCode")),
        flow_title=info.get("flowTitle"),
        latin_name=info.get("lVal18"),
        board_code=info.get("cgrValCot"),
        board_title=info.get("cgrValCotTitle"),
        c_com_val=info.get("cComVal"),
        instrument_type=to_optional_str(info.get("yVal")),
        nav=to_optional_float(info.get("nav")),
        contract_size=to_optional_int(info.get("contractSize")),
        etf_issued_units=to_optional_int(info.get("etfIssuedUnit")),
        etf_unit_date=to_optional_date(info.get("etfUnitDeven")),
        fara_desc=info.get("faraDesc"),
        under_supervision=to_optional_int(info.get("underSupervision")),
        top_inst=to_optional_int(info.get("topInst")),
        source_id=to_optional_int(info.get("sourceID")),
        last_date=to_optional_int(info.get("lastDate")),
        date=to_optional_date(info.get("dEven")),
        c_val_mne=info.get("cValMne"),
        c_soc_csac=info.get("cSocCSAC"),
        l_soc30=info.get("lSoc30"),
        market_code=info.get("yMarNSC"),
    )


def fetch_instrument_info(
    ins_code: str,
    session: Optional[requests.Session] = None,
    timeout: float = 20,
) -> InstrumentInfo:
    """GET and parse TSE_INSTRUMENT_INFO of an instrument."""
    return parse_instrument_info(
        get_json(
            tse_settings.TSE_INSTRUMENT_INFO.format(ins_code),
            session=session,
            timeout=timeout,
        )
    )


# ---------------------------------------------------------------------------
# Instrument/GetInstrumentSearch/{text} (TSE_SYMBOL_ID_URL)


@dataclass(frozen=True, slots=True)
class InstrumentSearchResult:
    """One instrument found by the symbol search (key instrumentSearch).

    The search matches the symbol or the name and returns at most about
    40 rows, active and deleted instruments.
    """

    # insCode: instrument code
    ins_code: str
    # lVal18AFC: نماد (symbol)
    symbol: Optional[str]
    # lastDate: 0 for an old deleted instrument, shown as
    # "(نماد قدیمی حذف شده)", 1 otherwise
    last_date: int
    # lVal30: نام (name)
    name: Optional[str] = None
    # flow: market, 1 بورس, 2 فرابورس, ...
    flow: Optional[int] = None
    # flowTitle: بازار, e.g. "بازار بورس"
    flow_title: Optional[str] = None
    # cgrValCot: board code, e.g. "N1"; "E1" for the energy exchange
    board_code: Optional[str] = None
    # cgrValCotTitle: board, often empty
    board_title: Optional[str] = None
    # insCode2: instrument of the odd lot market (خرده فروشی) of the
    # symbol
    retail_ins_code: Optional[str] = None
    # insCode3: instrument of the compensatory market (جبرانی)
    compensatory_ins_code: Optional[str] = None
    # insCode4: instrument of the block trade market (عمده)
    block_ins_code: Optional[str] = None
    # sourceID: 1 for بورس, 2 for فرابورس
    source_id: Optional[int] = None
    # cIsin: null in every row seen
    company_isin: Optional[str] = None
    # instrumentID: null in every row seen
    isin: Optional[str] = None
    # cComVal: null in every row seen
    c_com_val: Optional[str] = None
    # zTitad: 0 in every row seen
    total_shares: Optional[int] = None
    # baseVol: 0 in every row seen
    base_volume: Optional[int] = None

    @property
    def is_deleted(self) -> bool:
        """True for an old deleted instrument (نماد قدیمی حذف شده)."""
        return not self.last_date


def parse_instrument_search(data: Any) -> List[InstrumentSearchResult]:
    """Parse the JSON of Instrument/GetInstrumentSearch/{text}."""
    return [
        InstrumentSearchResult(
            ins_code=str(row["insCode"]),
            symbol=row["lVal18AFC"],
            last_date=int(row["lastDate"] or 0),
            name=row.get("lVal30"),
            flow=to_optional_int(row.get("flow")),
            flow_title=row.get("flowTitle"),
            board_code=row.get("cgrValCot"),
            board_title=row.get("cgrValCotTitle"),
            retail_ins_code=to_optional_str(row.get("insCode2")),
            compensatory_ins_code=to_optional_str(row.get("insCode3")),
            block_ins_code=to_optional_str(row.get("insCode4")),
            source_id=to_optional_int(row.get("sourceID")),
            company_isin=row.get("cIsin"),
            isin=row.get("instrumentID"),
            c_com_val=row.get("cComVal"),
            total_shares=to_optional_int(row.get("zTitad")),
            base_volume=to_optional_int(row.get("baseVol")),
        )
        for row in data.get("instrumentSearch") or []
    ]


def instrument_search_url(text: str) -> str:
    """TSE_SYMBOL_ID_URL of a text, URL encoded."""
    return tse_settings.TSE_SYMBOL_ID_URL.format(quote(text.strip(), safe=""))


def fetch_instrument_search(
    text: str,
    session: Optional[requests.Session] = None,
    timeout: float = 30,
) -> List[InstrumentSearchResult]:
    """GET and parse TSE_SYMBOL_ID_URL of a text (at least 2 letters)."""
    return parse_instrument_search(
        get_json(instrument_search_url(text), session=session, timeout=timeout)
    )


# ---------------------------------------------------------------------------
# Instrument/GetInstrumentHistory/{insCode}/{date}
# (SYMBOL_DAY_INSTRUMENT_INFO_URL)


@dataclass(frozen=True, slots=True)
class InstrumentHistory:
    """Information of an instrument on a past day (key
    instrumentHistory)."""

    # zTitad: تعداد سهام (total shares) on that day
    total_shares: int
    # baseVol: حجم مبنا (base volume) on that day, shares
    base_volume: int
    # lVal18AFC: نماد (symbol)
    symbol: Optional[str] = None
    # lVal30: نام (name)
    name: Optional[str] = None
    # flow: market, 1 بورس, 2 فرابورس, ...
    flow: Optional[int] = None
    # flowTitle: بازار, e.g. "بازار بورس"
    flow_title: Optional[str] = None
    # instrumentID: کد 12 رقمی نماد (ISIN of the symbol)
    isin: Optional[str] = None
    # cIsin: کد 12 رقمی شرکت (ISIN of the company)
    company_isin: Optional[str] = None
    # cgrValCot: board code, e.g. "N1"
    board_code: Optional[str] = None
    # cgrValCotTitle: board, e.g. "بازار اول (تابلوی اصلی) بورس"
    board_title: Optional[str] = None
    # cComVal: کد تابلو, e.g. "1"
    c_com_val: Optional[str] = None
    # insCode: "0" in every answer seen
    ins_code: Optional[str] = None
    # lastDate: 0 in every answer seen
    last_date: Optional[int] = None
    # sourceID: 0 in every answer seen
    source_id: Optional[int] = None


def parse_instrument_history(data: Any) -> InstrumentHistory:
    """Parse the JSON of Instrument/GetInstrumentHistory/{insCode}/{date}."""
    history = data["instrumentHistory"]
    return InstrumentHistory(
        total_shares=int(history["zTitad"]),
        base_volume=int(history["baseVol"]),
        symbol=history.get("lVal18AFC"),
        name=history.get("lVal30"),
        flow=to_optional_int(history.get("flow")),
        flow_title=history.get("flowTitle"),
        isin=history.get("instrumentID"),
        company_isin=history.get("cIsin"),
        board_code=history.get("cgrValCot"),
        board_title=history.get("cgrValCotTitle"),
        c_com_val=history.get("cComVal"),
        ins_code=to_optional_str(history.get("insCode")),
        last_date=to_optional_int(history.get("lastDate")),
        source_id=to_optional_int(history.get("sourceID")),
    )


def fetch_instrument_history(
    ins_code: str,
    date: datetime.date,
    session: Optional[requests.Session] = None,
    timeout: float = 30,
) -> InstrumentHistory:
    """GET and parse SYMBOL_DAY_INSTRUMENT_INFO_URL of an instrument on a
    day."""
    return parse_instrument_history(
        get_json(
            tse_settings.SYMBOL_DAY_INSTRUMENT_INFO_URL.format(
                index=ins_code, date=date.strftime(tse_settings.DATE_FORMAT)
            ),
            session=session,
            timeout=timeout,
        )
    )
