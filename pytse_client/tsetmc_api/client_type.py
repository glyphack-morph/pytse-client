"""Individual and corporate (حقیقی / حقوقی) trades: live for one or every
instrument, and the daily history of one instrument.

tse_settings constants and the pages that call them:

- TSE_CLIENT_TYPE_URL, ClientType/GetClientType/{insCode}/1/0: instInfo,
  tab "در یک نگاه", the "حقیقی / حقوقی" box, polled with the price box.
- CLIENT_TYPES_URL, ClientType/GetClientTypeAll: market watch, toolbar
  "تنظیمات دیده بان" > "اطلاعات تکمیلی" > button "حقیقی و حقوقی".
- TSE_CLIENT_TYPE_DATA_URL, ClientType/GetClientTypeHistory/{insCode}:
  instInfo, tab "حقیقی-حقوقی".

Also the TradeSummary type of Ticker.get_ticker_real_time_info_response
and the functions that make it.

Individual is حقیقی (I in the keys), corporate is حقوقی (N in the keys).
Volumes are in shares, values in rial.
"""

import datetime
from dataclasses import dataclass
from typing import Any, List, Optional

import requests
from pytse_client import tse_settings
from pytse_client.tsetmc_api._convert import to_date, to_optional_int
from pytse_client.utils.request_session import get_json

# ---------------------------------------------------------------------------
# ClientType/GetClientType/{insCode}/1/0 (TSE_CLIENT_TYPE_URL) and
# ClientType/GetClientTypeAll (CLIENT_TYPES_URL)


@dataclass(frozen=True, slots=True)
class ClientType:
    """Today's individual and corporate totals of an instrument: key
    clientType of GetClientType, or a row of key clientTypeAllDto of
    GetClientTypeAll (the same fields plus insCode)."""

    # buy_I_Volume: حجم خرید حقیقی
    individual_buy_volume: int
    # buy_CountI: تعداد خرید حقیقی (number of buyers)
    individual_buy_count: int
    # sell_I_Volume: حجم فروش حقیقی
    individual_sell_volume: int
    # sell_CountI: تعداد فروش حقیقی (number of sellers)
    individual_sell_count: int
    # buy_N_Volume: حجم خرید حقوقی
    corporate_buy_volume: int
    # buy_CountN: تعداد خرید حقوقی
    corporate_buy_count: int
    # sell_N_Volume: حجم فروش حقوقی
    corporate_sell_volume: int
    # sell_CountN: تعداد فروش حقوقی
    corporate_sell_count: int
    # insCode: instrument code, only in the rows of GetClientTypeAll
    ins_code: Optional[str] = None
    # buy_DDD_Volume: 0 in every answer seen, not shown on the website
    ddd_buy_volume: Optional[int] = None
    # buy_CountDDD: 0 in every answer seen, not shown on the website
    ddd_buy_count: Optional[int] = None


def _parse_client_type(row: Any, ins_code: Optional[str]) -> ClientType:
    return ClientType(
        individual_buy_volume=int(row["buy_I_Volume"]),
        individual_buy_count=int(row["buy_CountI"]),
        individual_sell_volume=int(row["sell_I_Volume"]),
        individual_sell_count=int(row["sell_CountI"]),
        corporate_buy_volume=int(row["buy_N_Volume"]),
        corporate_buy_count=int(row["buy_CountN"]),
        corporate_sell_volume=int(row["sell_N_Volume"]),
        corporate_sell_count=int(row["sell_CountN"]),
        ins_code=ins_code,
        ddd_buy_volume=to_optional_int(row.get("buy_DDD_Volume")),
        ddd_buy_count=to_optional_int(row.get("buy_CountDDD")),
    )


def parse_client_type(data: Any) -> Optional[ClientType]:
    """Parse the JSON of ClientType/GetClientType/{insCode}/1/0, None when
    the API sends no totals."""
    client_type = data["clientType"]
    if not client_type:
        return None
    return _parse_client_type(client_type, client_type.get("insCode"))


def fetch_client_type(
    ins_code: str,
    session: Optional[requests.Session] = None,
    timeout: float = 30,
) -> Optional[ClientType]:
    """GET and parse TSE_CLIENT_TYPE_URL of an instrument."""
    return parse_client_type(
        get_json(
            tse_settings.TSE_CLIENT_TYPE_URL.format(ins_code),
            session=session,
            timeout=timeout,
        )
    )


def parse_client_type_all(data: Any) -> List[ClientType]:
    """Parse the JSON of ClientType/GetClientTypeAll, one row per
    instrument traded today."""
    return [
        _parse_client_type(row, str(row["insCode"]))
        for row in data["clientTypeAllDto"] or []
    ]


def fetch_client_type_all(
    session: Optional[requests.Session] = None, timeout: float = 120
) -> List[ClientType]:
    """GET and parse CLIENT_TYPES_URL."""
    return parse_client_type_all(
        get_json(
            tse_settings.CLIENT_TYPES_URL, session=session, timeout=timeout
        )
    )


# TradeSummary is the public type of
# RealtimeTickerInfo.individual_trade_summary and corporate_trade_summary
# (importable from pytse_client.ticker.api_extractors as before), it is
# not frozen and keeps its float fields to stay as it was.
@dataclass
class TradeSummary:
    buy_vol: float
    buy_count: float
    sell_vol: float
    sell_count: float


def individual_trade_summary(
    client_type: Optional[ClientType],
) -> Optional[TradeSummary]:
    """Individual (حقیقی) part of today's totals."""
    if client_type is None:
        return None
    return TradeSummary(
        buy_vol=float(client_type.individual_buy_volume),
        buy_count=float(client_type.individual_buy_count),
        sell_vol=float(client_type.individual_sell_volume),
        sell_count=float(client_type.individual_sell_count),
    )


def corporate_trade_summary(
    client_type: Optional[ClientType],
) -> Optional[TradeSummary]:
    """Corporate (حقوقی) part of today's totals."""
    if client_type is None:
        return None
    return TradeSummary(
        buy_vol=float(client_type.corporate_buy_volume),
        buy_count=float(client_type.corporate_buy_count),
        sell_vol=float(client_type.corporate_sell_volume),
        sell_count=float(client_type.corporate_sell_count),
    )


# ---------------------------------------------------------------------------
# ClientType/GetClientTypeHistory/{insCode} (TSE_CLIENT_TYPE_DATA_URL)


@dataclass(frozen=True, slots=True)
class ClientTypeHistory:
    """Individual and corporate totals of one day (key clientType), a
    block of tab "حقیقی-حقوقی"."""

    # recDate: day
    date: datetime.date
    # buy_I_Count: تعداد خرید حقیقی (number of buyers)
    individual_buy_count: int
    # buy_N_Count: تعداد خرید حقوقی
    corporate_buy_count: int
    # sell_I_Count: تعداد فروش حقیقی (number of sellers)
    individual_sell_count: int
    # sell_N_Count: تعداد فروش حقوقی
    corporate_sell_count: int
    # buy_I_Volume: حجم خرید حقیقی
    individual_buy_volume: int
    # buy_N_Volume: حجم خرید حقوقی
    corporate_buy_volume: int
    # sell_I_Volume: حجم فروش حقیقی
    individual_sell_volume: int
    # sell_N_Volume: حجم فروش حقوقی
    corporate_sell_volume: int
    # buy_I_Value: ارزش خرید حقیقی, rial
    individual_buy_value: int
    # buy_N_Value: ارزش خرید حقوقی, rial
    corporate_buy_value: int
    # sell_I_Value: ارزش فروش حقیقی, rial
    individual_sell_value: int
    # sell_N_Value: ارزش فروش حقوقی, rial
    corporate_sell_value: int
    # insCode: instrument code
    ins_code: Optional[str] = None


def parse_client_type_history(data: Any) -> List[ClientTypeHistory]:
    """Parse the JSON of ClientType/GetClientTypeHistory/{insCode}, newest
    day first."""
    return [
        ClientTypeHistory(
            date=to_date(row["recDate"]),
            individual_buy_count=int(row["buy_I_Count"]),
            corporate_buy_count=int(row["buy_N_Count"]),
            individual_sell_count=int(row["sell_I_Count"]),
            corporate_sell_count=int(row["sell_N_Count"]),
            individual_buy_volume=int(row["buy_I_Volume"]),
            corporate_buy_volume=int(row["buy_N_Volume"]),
            individual_sell_volume=int(row["sell_I_Volume"]),
            corporate_sell_volume=int(row["sell_N_Volume"]),
            individual_buy_value=int(row["buy_I_Value"]),
            corporate_buy_value=int(row["buy_N_Value"]),
            individual_sell_value=int(row["sell_I_Value"]),
            corporate_sell_value=int(row["sell_N_Value"]),
            ins_code=row.get("insCode"),
        )
        for row in data["clientType"] or []
    ]


def fetch_client_type_history(
    ins_code: str,
    session: Optional[requests.Session] = None,
    timeout: float = 60,
) -> List[ClientTypeHistory]:
    """GET and parse TSE_CLIENT_TYPE_DATA_URL of an instrument."""
    return parse_client_type_history(
        get_json(
            tse_settings.TSE_CLIENT_TYPE_DATA_URL.format(ins_code),
            session=session,
            timeout=timeout,
        )
    )
