"""Trades (ریز معاملات) of an instrument: today and on a past day.

tse_settings constants and the pages that call them:

- TSE_TRADE_DETAIL_URL, Trade/GetTrade/{insCode}: instInfo, loaded with the
  page (intraday chart of tab "در یک نگاه"); the same data is shown by the
  header button "اطلاعات تکمیلی" > "معاملات" > "ریز معاملات".
- TICKER_TRADE_DETAILS, Trade/GetTradeHistory/{insCode}/{date}/false:
  History page, tab "معاملات".

Both answer a list of the same rows. Prices are in rial, volumes in
shares.
"""

import datetime
from dataclasses import dataclass
from typing import Any, List, Optional

import requests
from pytse_client import tse_settings
from pytse_client.tsetmc_api._convert import (
    to_optional_date,
    to_optional_int,
    to_time,
)
from pytse_client.utils.request_session import get_json


@dataclass(frozen=True, slots=True)
class Trade:
    """One trade (key trade of GetTrade, tradeHistory of
    GetTradeHistory). The API sometimes returns a trade twice, number
    tells them apart."""

    # nTran: number of the trade in the day (شماره معامله)
    number: int
    # hEven: زمان (time of the trade)
    time: datetime.time
    # qTitTran: حجم (volume), shares
    volume: int
    # pTran: قیمت (price), rial
    price: int
    # canceled: 1 for a canceled trade (struck through on the website)
    canceled: bool
    # insCode: null in every row seen
    ins_code: Optional[str] = None
    # dEven: 0 (no date) in every row seen
    date: Optional[datetime.date] = None
    # qTitNgJ: 0 in every row seen, meaning unknown
    q_tit_ng_j: Optional[int] = None
    # iSensVarP: "\x00" in every row seen, meaning unknown
    i_sens_var_p: Optional[str] = None
    # pPhSeaCotJ: 0 in every row seen, probably the day high at the trade
    p_ph_sea_cot_j: Optional[int] = None
    # pPbSeaCotJ: 0 in every row seen, probably the day low at the trade
    p_pb_sea_cot_j: Optional[int] = None
    # iAnuTran: 0 in every row seen, meaning unknown
    i_anu_tran: Optional[int] = None
    # xqVarPJDrPRf: 0 in every row seen, meaning unknown
    xq_var_pj_dr_p_rf: Optional[float] = None


def _parse_trades(rows: Any) -> List[Trade]:
    return [
        Trade(
            number=int(row["nTran"]),
            time=to_time(row["hEven"]),
            volume=int(row["qTitTran"]),
            price=int(row["pTran"]),
            canceled=bool(row["canceled"]),
            ins_code=row.get("insCode"),
            date=to_optional_date(row.get("dEven")),
            q_tit_ng_j=to_optional_int(row.get("qTitNgJ")),
            i_sens_var_p=row.get("iSensVarP"),
            p_ph_sea_cot_j=to_optional_int(row.get("pPhSeaCotJ")),
            p_pb_sea_cot_j=to_optional_int(row.get("pPbSeaCotJ")),
            i_anu_tran=to_optional_int(row.get("iAnuTran")),
            xq_var_pj_dr_p_rf=row.get("xqVarPJDrPRf"),
        )
        for row in rows or []
    ]


def parse_trades(data: Any) -> List[Trade]:
    """Parse the JSON of Trade/GetTrade/{insCode} (tens of thousands of
    rows), canceled and repeated trades included."""
    return _parse_trades(data["trade"])


def fetch_trades(
    ins_code: str,
    session: Optional[requests.Session] = None,
    timeout: float = 60,
) -> List[Trade]:
    """GET and parse TSE_TRADE_DETAIL_URL of an instrument."""
    return parse_trades(
        get_json(
            tse_settings.TSE_TRADE_DETAIL_URL.format(ins_code),
            session=session,
            timeout=timeout,
        )
    )


def parse_trade_history(data: Any) -> List[Trade]:
    """Parse the JSON of Trade/GetTradeHistory/{insCode}/{date}/false
    (tens of thousands of rows), canceled and repeated trades included."""
    return _parse_trades(data["tradeHistory"])


def fetch_trade_history(
    ins_code: str,
    date: datetime.date,
    session: Optional[requests.Session] = None,
    timeout: float = 100,
) -> List[Trade]:
    """GET and parse TICKER_TRADE_DETAILS of an instrument on a day."""
    return parse_trade_history(
        get_json(
            tse_settings.TICKER_TRADE_DETAILS.format(
                index=ins_code, date=date.strftime(tse_settings.DATE_FORMAT)
            ),
            session=session,
            timeout=timeout,
        )
    )


def unique_trades(trades: List[Trade]) -> List[Trade]:
    """Trades that were not canceled, each one once.

    The API sometimes returns a trade twice; a repeated trade keeps the
    place of its first copy, like a dict keyed by number.
    """
    by_number = {}
    for trade in trades:
        if not trade.canceled:
            by_number[trade.number] = trade
    return list(by_number.values())
