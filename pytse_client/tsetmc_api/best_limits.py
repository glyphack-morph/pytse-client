"""Order book (best limits, خرید / فروش) of an instrument: live and on a
past day.

tse_settings constants and the pages that call them:

- TSE_BEST_LIMITS_URL, BestLimits/{insCode}: instInfo, tab "در یک نگاه",
  the order box (خرید / فروش), polled with the price box.
- TICKER_ORDER_BOOK, BestLimits/{insCode}/{date}: History page, tab
  "در یک نگاه", box "خرید / فروش" that follows the time slider (زمان).

Also the Order type of Ticker.get_ticker_real_time_info_response and
orders_from_best_limits, which turns the rows into buy and sell orders.

Prices are in rial, volumes in shares.
"""

import datetime
from dataclasses import dataclass
from typing import Any, List, Optional, Sequence, Tuple

import requests
from pytse_client import tse_settings
from pytse_client.tsetmc_api._convert import to_optional_date, to_time
from pytse_client.utils.request_session import get_json

# ---------------------------------------------------------------------------
# BestLimits/{insCode} (TSE_BEST_LIMITS_URL)


@dataclass(frozen=True, slots=True)
class BestLimit:
    """One level of the live order book (key bestLimits), a row of the
    order box: buy (خرید) on the right, sell (فروش) on the left."""

    # number: level (ردیف), 1 to 5, 1 is the best price
    level: int
    # zOrdMeDem: خرید تعداد, number of buy orders
    buy_count: int
    # qTitMeDem: خرید حجم, shares
    buy_volume: int
    # pMeDem: خرید قیمت, rial
    buy_price: int
    # pMeOf: فروش قیمت, rial
    sell_price: int
    # qTitMeOf: فروش حجم, shares
    sell_volume: int
    # zOrdMeOf: فروش تعداد, number of sell orders
    sell_count: int
    # title: null in every answer seen
    title: Optional[str] = None
    # insCode: null in every answer seen
    ins_code: Optional[str] = None


def parse_best_limits(data: Any) -> List[BestLimit]:
    """Parse the JSON of BestLimits/{insCode}, in the order of the API."""
    return [
        BestLimit(
            level=int(row["number"]),
            buy_count=int(row["zOrdMeDem"]),
            buy_volume=int(row["qTitMeDem"]),
            buy_price=int(row["pMeDem"]),
            sell_price=int(row["pMeOf"]),
            sell_volume=int(row["qTitMeOf"]),
            sell_count=int(row["zOrdMeOf"]),
            title=row.get("title"),
            ins_code=row.get("insCode"),
        )
        for row in data["bestLimits"] or []
    ]


def fetch_best_limits(
    ins_code: str,
    session: Optional[requests.Session] = None,
    timeout: float = 30,
) -> List[BestLimit]:
    """GET and parse TSE_BEST_LIMITS_URL of an instrument."""
    return parse_best_limits(
        get_json(
            tse_settings.TSE_BEST_LIMITS_URL.format(ins_code),
            session=session,
            timeout=timeout,
        )
    )


# Order is the public type of RealtimeTickerInfo.buy_orders and
# sell_orders (importable from pytse_client.ticker.api_extractors as
# before), it is not frozen to stay as it was.
@dataclass
class Order:
    count: int
    volume: int
    price: int


def orders_from_best_limits(
    best_limits: Sequence[BestLimit],
) -> Tuple[List[Order], List[Order]]:
    """Buy orders (تقاضا) and sell orders (عرضه), best price first."""
    buy_orders = []
    sell_orders = []
    for row in sorted(best_limits, key=lambda row: row.level):
        buy_orders.append(
            Order(
                count=row.buy_count,
                volume=row.buy_volume,
                price=row.buy_price,
            )
        )
        sell_orders.append(
            Order(
                count=row.sell_count,
                volume=row.sell_volume,
                price=row.sell_price,
            )
        )
    return buy_orders, sell_orders


# ---------------------------------------------------------------------------
# BestLimits/{insCode}/{date} (TICKER_ORDER_BOOK)


@dataclass(frozen=True, slots=True)
class BestLimitHistory:
    """One change of one level of the order book on a past day (key
    bestLimitsHistory). The state at a time is the last change of each
    level up to that time."""

    # hEven: time of the change
    time: datetime.time
    # refID: id of the change, increases with time
    ref_id: int
    # number: level (ردیف), 1 to 5, 1 is the best price
    level: int
    # zOrdMeDem: خرید تعداد, number of buy orders
    buy_count: int
    # qTitMeDem: خرید حجم, shares
    buy_volume: int
    # pMeDem: خرید قیمت, rial
    buy_price: int
    # pMeOf: فروش قیمت, rial
    sell_price: int
    # qTitMeOf: فروش حجم, shares
    sell_volume: int
    # zOrdMeOf: فروش تعداد, number of sell orders
    sell_count: int
    # idn: 0 in every row seen
    idn: Optional[int] = None
    # dEven: 0 (no date) in every row seen
    date: Optional[datetime.date] = None
    # title: null in every row seen
    title: Optional[str] = None
    # insCode: null in every row seen
    ins_code: Optional[str] = None


def parse_best_limits_history(data: Any) -> List[BestLimitHistory]:
    """Parse the JSON of BestLimits/{insCode}/{date} (tens of thousands of
    rows), in the order of the API."""
    return [
        BestLimitHistory(
            time=to_time(row["hEven"]),
            ref_id=int(row["refID"]),
            level=int(row["number"]),
            buy_count=int(row["zOrdMeDem"]),
            buy_volume=int(row["qTitMeDem"]),
            buy_price=int(row["pMeDem"]),
            sell_price=int(row["pMeOf"]),
            sell_volume=int(row["qTitMeOf"]),
            sell_count=int(row["zOrdMeOf"]),
            idn=row.get("idn"),
            date=to_optional_date(row.get("dEven")),
            title=row.get("title"),
            ins_code=row.get("insCode"),
        )
        for row in data["bestLimitsHistory"] or []
    ]


def fetch_best_limits_history(
    ins_code: str,
    date: datetime.date,
    session: Optional[requests.Session] = None,
    timeout: float = 30,
) -> List[BestLimitHistory]:
    """GET and parse TICKER_ORDER_BOOK of an instrument on a day."""
    return parse_best_limits_history(
        get_json(
            tse_settings.TICKER_ORDER_BOOK.format(
                index=ins_code, date=date.strftime(tse_settings.DATE_FORMAT)
            ),
            session=session,
            timeout=timeout,
        )
    )
