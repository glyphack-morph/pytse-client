"""Major shareholders (سهامداران عمده) of an instrument: the latest list
and the list of a past day.

tse_settings constants and the pages that call them:

- TSE_SHAREHOLDERS_URL, Shareholder/GetInstrumentShareHolderLast/{insCode}:
  instInfo, tab "سهامداران" (سهامداران/دارندگان در پایان روز).
- SYMBOL_DAY_INFO_SHAREHOLDERS_DATA, Shareholder/{insCode}/{date}: History
  page, tab "در یک نگاه", box "سهامداران" (قبل از آغاز معاملات).

Both answer a list of the same rows.
"""

import datetime
from dataclasses import dataclass
from typing import Any, List, Optional

import requests
from pytse_client import tse_settings
from pytse_client.tsetmc_api._convert import to_optional_date
from pytse_client.utils.request_session import get_json


@dataclass(frozen=True, slots=True)
class Shareholder:
    """One major shareholder (key shareHolder of
    GetInstrumentShareHolderLast, shareShareholder of Shareholder/{date})."""

    # shareHolderShareID: id of the holding, the website uses it to show
    # the history of this shareholder
    share_id: int
    # shareHolderName: سهامدار/دارنده
    name: str
    # cIsin: ISIN of the company (کد 12 رقمی شرکت), e.g. "IRO1FOLD0009"
    company_isin: str
    # dEven: day of the list; 0 (None) in GetInstrumentShareHolderLast.
    # Shareholder/{date} also returns the list of the next trading day.
    date: Optional[datetime.date]
    # numberOfShares: سهم (shares held)
    shares: int
    # perOfShares: درصد (percent of all shares)
    percentage: float
    # change: arrow of the website, 2 more shares (ArrowUp), 3 fewer
    # (ArrowDown), 1 no change
    change: int
    # changeAmount: تغییر (change of shares held)
    change_amount: int
    # shareHolderID: 0 in every row seen
    shareholder_id: Optional[int] = None


def _parse_shareholders(rows: Any) -> List[Shareholder]:
    return [
        Shareholder(
            share_id=int(row["shareHolderShareID"]),
            name=row["shareHolderName"],
            company_isin=row["cIsin"],
            date=to_optional_date(row["dEven"]),
            shares=int(row["numberOfShares"]),
            percentage=float(row["perOfShares"]),
            change=int(row["change"]),
            change_amount=int(row["changeAmount"]),
            shareholder_id=row.get("shareHolderID"),
        )
        for row in rows or []
    ]


def parse_shareholders(data: Any) -> List[Shareholder]:
    """Parse the JSON of Shareholder/GetInstrumentShareHolderLast/{insCode}."""
    return _parse_shareholders(data["shareHolder"])


def fetch_shareholders(
    ins_code: str,
    session: Optional[requests.Session] = None,
    timeout: float = 30,
) -> List[Shareholder]:
    """GET and parse TSE_SHAREHOLDERS_URL of an instrument."""
    return parse_shareholders(
        get_json(
            tse_settings.TSE_SHAREHOLDERS_URL.format(ins_code),
            session=session,
            timeout=timeout,
        )
    )


def parse_day_shareholders(data: Any) -> List[Shareholder]:
    """Parse the JSON of Shareholder/{insCode}/{date}: the shareholders of
    that day and of the next trading day (see Shareholder.date)."""
    return _parse_shareholders(data["shareShareholder"])


def fetch_day_shareholders(
    ins_code: str,
    date: datetime.date,
    session: Optional[requests.Session] = None,
    timeout: float = 30,
) -> List[Shareholder]:
    """GET and parse SYMBOL_DAY_INFO_SHAREHOLDERS_DATA of an instrument on
    a day."""
    return parse_day_shareholders(
        get_json(
            tse_settings.SYMBOL_DAY_INFO_SHAREHOLDERS_DATA.format(
                index=ins_code, date=date.strftime(tse_settings.DATE_FORMAT)
            ),
            session=session,
            timeout=timeout,
        )
    )
