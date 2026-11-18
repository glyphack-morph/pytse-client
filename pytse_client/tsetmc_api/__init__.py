"""Typed responses of the TSETMC JSON API (https://cdn.tsetmc.com/api/...).

Every endpoint of pytse_client.tse_settings has a frozen dataclass that
documents what it returns (one field per JSON key, with the key and the
label of the website in a comment) and a pure parse function that turns
the decoded JSON into it. Parse functions do no network I/O, so the sync
code (utils.get_json) and the async code (aiohttp) share them; the
fetch_* helpers GET an endpoint with utils.get_json and parse it.

Fields the library reads are required: parsing fails with a KeyError when
the API drops one. The other fields are Optional with a default, so the
API can drop them.

The tse_settings constant and parse function of every endpoint, by module
(the module docstrings name the API paths and the pages that call them):

market
    TSE_GET_LAST_TRADE_DAY: parse_market_overview
    MARKET_WATCH_URL: parse_market_watch
    KEY_STATS_URL: parse_key_stats
closing_price
    TSE_CLOSING_PRICE_INFO_URL: parse_closing_price_info
    TSE_TICKER_EXPORT_DATA_ADDRESS: parse_closing_price_daily_list
    TSE_TICKER_RECENT_DAYS_URL: parse_closing_price_daily_list
    CLOSING_PRICE_DAILY_ALL_INST_URL: parse_closing_price_daily_all_inst
best_limits
    TSE_BEST_LIMITS_URL: parse_best_limits
    TICKER_ORDER_BOOK: parse_best_limits_history
client_type
    TSE_CLIENT_TYPE_URL: parse_client_type
    CLIENT_TYPES_URL: parse_client_type_all
    TSE_CLIENT_TYPE_DATA_URL: parse_client_type_history
trade
    TSE_TRADE_DETAIL_URL: parse_trades
    TICKER_TRADE_DETAILS: parse_trade_history
shareholder
    TSE_SHAREHOLDERS_URL: parse_shareholders
    SYMBOL_DAY_INFO_SHAREHOLDERS_DATA: parse_day_shareholders
instrument
    TSE_INSTRUMENT_INFO: parse_instrument_info
    TSE_SYMBOL_ID_URL: parse_instrument_search
    SYMBOL_DAY_INSTRUMENT_INFO_URL: parse_instrument_history
index
    TSE_FINANCIAL_INDEX_EXPORT_DATA_ADDRESS: parse_index_history
    FINANCIAL_INDEX_EXPORT_INTRADAY_URL: parse_index_intraday
    INDICES_LIST_URL: parse_indices
    FINANCIAL_INDEX_COMPANIES_URL: parse_index_companies
fund
    TSE_ETF_URL: parse_etf
codal
    TSE_TICKER_INTRODUCTION_URL: parse_codal_publisher

TSE_TICKER_ADDRESS is the page of a symbol on the website, not an API.
"""

from pytse_client.tsetmc_api.best_limits import (
    BestLimit,
    BestLimitHistory,
    Order,
    fetch_best_limits,
    fetch_best_limits_history,
    orders_from_best_limits,
    parse_best_limits,
    parse_best_limits_history,
)
from pytse_client.tsetmc_api.client_type import (
    ClientType,
    ClientTypeHistory,
    TradeSummary,
    corporate_trade_summary,
    fetch_client_type,
    fetch_client_type_all,
    fetch_client_type_history,
    individual_trade_summary,
    parse_client_type,
    parse_client_type_all,
    parse_client_type_history,
)
from pytse_client.tsetmc_api.closing_price import (
    ClosingPriceDaily,
    ClosingPriceDailyAllInst,
    ClosingPriceInfo,
    InstrumentState,
    fetch_closing_price_daily_all_inst,
    fetch_closing_price_daily_list,
    fetch_closing_price_info,
    fetch_recent_closing_price_daily_list,
    parse_closing_price_daily_all_inst,
    parse_closing_price_daily_list,
    parse_closing_price_info,
)
from pytse_client.tsetmc_api.codal import (
    CodalPublisher,
    fetch_codal_publisher,
    parse_codal_publisher,
)
from pytse_client.tsetmc_api.fund import Etf, fetch_etf, parse_etf
from pytse_client.tsetmc_api.index import (
    IndexCompanies,
    IndexCompany,
    IndexCompanyClosingPrice,
    IndexCompanyInstrument,
    IndexHistory,
    IndexIntraday,
    IndexLastValue,
    fetch_index_companies,
    fetch_index_history,
    fetch_index_intraday,
    fetch_indices,
    parse_index_companies,
    parse_index_history,
    parse_index_intraday,
    parse_indices,
)
from pytse_client.tsetmc_api.instrument import (
    InstrumentEps,
    InstrumentHistory,
    InstrumentInfo,
    InstrumentSearchResult,
    InstrumentSector,
    StaticThreshold,
    fetch_instrument_history,
    fetch_instrument_info,
    fetch_instrument_search,
    instrument_search_url,
    parse_instrument_history,
    parse_instrument_info,
    parse_instrument_search,
)
from pytse_client.tsetmc_api.market import (
    InstrumentStatistic,
    MarketOverview,
    MarketWatchBestLimit,
    MarketWatchInstrument,
    fetch_key_stats,
    fetch_market_overview,
    fetch_market_watch,
    parse_key_stats,
    parse_market_overview,
    parse_market_watch,
)
from pytse_client.tsetmc_api.shareholder import (
    Shareholder,
    fetch_day_shareholders,
    fetch_shareholders,
    parse_day_shareholders,
    parse_shareholders,
)
from pytse_client.tsetmc_api.trade import (
    Trade,
    fetch_trade_history,
    fetch_trades,
    parse_trade_history,
    parse_trades,
    unique_trades,
)
