"""NAV of exchange traded funds (ETF, صندوق های قابل معامله).

tse_settings constant and the page that calls it:

- TSE_ETF_URL, Fund/GetETFByInsCode/{insCode}: instInfo of a fund (e.g.
  ياقوت, 1438514795814416), tab "در یک نگاه", rows "NAV ابطال" and
  "زمان اعلام", polled every 60 seconds. The API answers HTTP 500 for
  instruments that are not funds.

Prices are in rial.
"""

import datetime
from dataclasses import dataclass
from typing import Any, Optional

import requests
from pytse_client import tse_settings
from pytse_client.tsetmc_api._convert import (
    to_optional_date,
    to_optional_int,
    to_optional_time,
)
from pytse_client.utils.request_session import get_json


@dataclass(frozen=True, slots=True)
class Etf:
    """NAV of a fund (key etf)."""

    # pRedTran: NAV ابطال (redemption NAV, قیمت ابطال), rial
    redemption_nav: Optional[int]
    # deven (lower case d): day of "زمان اعلام" (publish time of the NAV)
    date: Optional[datetime.date]
    # hEven: time of "زمان اعلام"
    time: Optional[datetime.time]
    # pSubTran: subscription NAV (قیمت صدور), rial
    subscription_nav: Optional[int] = None
    # insCode: instrument code
    ins_code: Optional[str] = None
    # iClose: 0 in every answer seen
    i_close: Optional[int] = None


def parse_etf(data: Any) -> Optional[Etf]:
    """Parse the JSON of Fund/GetETFByInsCode/{insCode}, None when the API
    sends no fund."""
    etf = data.get("etf")
    if not etf:
        return None
    return Etf(
        redemption_nav=to_optional_int(etf["pRedTran"]),
        date=to_optional_date(etf["deven"]),
        time=to_optional_time(etf["hEven"]),
        subscription_nav=to_optional_int(etf.get("pSubTran")),
        ins_code=etf.get("insCode"),
        i_close=etf.get("iClose"),
    )


def fetch_etf(
    ins_code: str,
    session: Optional[requests.Session] = None,
    timeout: float = 10,
) -> Optional[Etf]:
    """GET and parse TSE_ETF_URL of a fund. The API answers HTTP 500 for
    instruments that are not funds, so this raises a
    requests.RequestException for them."""
    return parse_etf(
        get_json(
            tse_settings.TSE_ETF_URL.format(ins_code),
            session=session,
            timeout=timeout,
        )
    )
