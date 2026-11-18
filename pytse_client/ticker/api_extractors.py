"""Helpers of the Ticker module, kept importable from here.

The responses of the TSETMC API are parsed in pytse_client.tsetmc_api;
these names point to it.
"""

from pytse_client.tsetmc_api.best_limits import Order, orders_from_best_limits
from pytse_client.tsetmc_api.client_type import (
    TradeSummary,
    corporate_trade_summary,
    individual_trade_summary,
)
from pytse_client.tsetmc_api.instrument import (
    InstrumentInfo,
    fetch_instrument_info,
)

__all__ = [
    "InstrumentInfo",
    "Order",
    "TradeSummary",
    "get_corporate_trade_summary",
    "get_individual_trade_summary",
    "get_instrument_info",
    "get_orders",
]

# buy and sell orders of the rows of BestLimits/{insCode}
get_orders = orders_from_best_limits
# individual (حقیقی) and corporate (حقوقی) part of
# ClientType/GetClientType/{insCode}/1/0
get_individual_trade_summary = individual_trade_summary
get_corporate_trade_summary = corporate_trade_summary


def get_instrument_info(ticket_id: str) -> InstrumentInfo:
    """Instrument information (Instrument/GetInstrumentInfo) of an
    insCode, see pytse_client.tsetmc_api.instrument."""
    return fetch_instrument_info(ticket_id)
