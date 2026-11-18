"""Build the list of market symbols (data/symbols_name.json).

Everything comes from the JSON API behind https://www.tsetmc.com (the old
website and its "all symbols" page, Loader.aspx?ParTree=111C1417, are gone).

Where the symbols come from (see scripts/update_symbols_json.py):

1. The market watch (دیده بان بازار), which lists every instrument that is
   listed and not suspended, with its symbol, name and ISIN.
2. The closing prices of every instrument for the last ~60 trading days,
   which also has instruments missing from the market watch (mostly
   suspended ones). Only their insCode is given, so their symbol, name and
   ISIN are read from the instrument info endpoint.
3. The current symbols_name.json, because no endpoint lists instruments
   that have been suspended for a long time; each of them is checked again
   with the symbol search. Deleted ones are kept (so their history can
   still be downloaded by symbol) with their index in their old list,
   which is how Ticker knows a symbol is deleted.

Every symbol is then looked up with the symbol search (جستجوی نماد), which
returns active and deleted (old) instruments; the website marks an
instrument as deleted ("نماد قدیمی حذف شده") when its lastDate is 0. That
gives the active insCode ("index") and the old insCodes of the symbol.
"""

import asyncio
import json
import locale
import logging
import re
from contextlib import asynccontextmanager
from dataclasses import dataclass, replace
from pathlib import Path
from typing import (
    Any,
    AsyncIterator,
    Dict,
    Iterable,
    List,
    Optional,
    Sequence,
    Set,
    Tuple,
    Union,
)

import aiohttp
import requests
from pytse_client import config, tse_settings
from pytse_client.tsetmc_api.closing_price import (
    fetch_closing_price_daily_all_inst,
)
from pytse_client.tsetmc_api.instrument import (
    InstrumentInfo,
    InstrumentSearchResult,
    fetch_instrument_info,
    fetch_instrument_search,
    instrument_search_url,
    parse_instrument_info,
    parse_instrument_search,
)
from pytse_client.tsetmc_api.market import (
    MarketWatchInstrument,
    fetch_market_watch,
)
from pytse_client.utils.persian import replace_arabic
from pytse_client.utils.request_session import requests_retry_session
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
    wait_random,
)
from yarl import URL

logger = logging.getLogger(config.LOGGER_NAME)

# see tse_settings.CLOSING_PRICE_DAILY_ALL_INST_URL
CLOSING_PRICE_DAILY_ALL_INST_URL = (
    tse_settings.CLOSING_PRICE_DAILY_ALL_INST_URL
)

# Number of requests sent to the API at the same time by the async helpers.
DEFAULT_CONCURRENCY = 5

_REQUEST_TIMEOUT = 30


@dataclass
class MarketSymbol:
    code: str
    symbol: str
    name: str
    index: str
    old: List[str]

    def __hash__(self):
        """Hash function is used for deduplication"""
        return hash(self.symbol)

    def __lt__(self, other):
        return not locale.strcoll(other.symbol, self.symbol) < 0

    def __eq__(self, other):
        return locale.strcoll(other.symbol, self.symbol) == 0


def clean_symbol(symbol: str) -> str:
    return replace_arabic(symbol.strip())


def clean_name(name: str) -> str:
    return replace_arabic(name.strip()).replace("‌", "").strip()


def _ends_with_number(symbol: str) -> bool:
    # symbols that end with a number are bonds, options, futures, commodity
    # certificates and the like, they are not wanted in the symbols list.
    return re.search(r"\d+$", symbol) is not None


def _unique(values: Iterable[str]) -> List[str]:
    seen: Set[str] = set()
    result = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def deduplicate_market_symbols(
    symbols: Iterable[MarketSymbol],
) -> List[MarketSymbol]:
    """Remove symbols that appear more than once, the first one is kept."""
    unique: Dict[str, MarketSymbol] = {}
    for symbol in symbols:
        unique.setdefault(symbol.symbol, symbol)
    return list(unique.values())


# ---------------------------------------------------------------------------
# collation

_FA_IR_LOCALES = ("fa_IR.UTF-8", "fa_IR.utf8", "fa_IR")
_PERSIAN_ALPHABET = "آاأإءبپتثجچحخدذرزژسشصضطظعغفقکگلمنوؤهةیئ"
_PERSIAN_ORDER = {char: i for i, char in enumerate(_PERSIAN_ALPHABET)}
_has_persian_collation = False


def set_persian_collation() -> bool:
    """Use the fa_IR collation (LC_COLLATE) to sort symbols.

    Returns False, and leaves the locale as it is, when no fa_IR locale is
    installed; sort_market_symbols then uses a simple Persian alphabet
    order. Generate the locale with
    ``sudo localedef -i fa_IR -f UTF-8 fa_IR.UTF-8`` (or uncomment fa_IR in
    /etc/locale.gen and run ``sudo locale-gen``).
    """
    global _has_persian_collation
    for name in _FA_IR_LOCALES:
        try:
            locale.setlocale(locale.LC_COLLATE, name)
        except locale.Error:
            continue
        _has_persian_collation = True
        return True
    logger.warning(
        "fa_IR locale is not installed, symbols are sorted by a simple "
        "Persian alphabet order instead (generate the locale with: "
        "sudo localedef -i fa_IR -f UTF-8 fa_IR.UTF-8)"
    )
    return False


def _persian_sort_key(text: str) -> Tuple:
    # used when the fa_IR locale is missing: letters in the order of the
    # Persian alphabet, after digits and other characters.
    return tuple(
        (1, _PERSIAN_ORDER[char]) if char in _PERSIAN_ORDER else (0, ord(char))
        for char in text
        if char not in " ‌"
    )


def sort_market_symbols(
    symbols: Iterable[MarketSymbol],
) -> List[MarketSymbol]:
    """Sort by symbol with the fa_IR collation (see set_persian_collation)."""
    if _has_persian_collation:
        return sorted(symbols)
    return sorted(
        symbols, key=lambda s: (_persian_sort_key(s.symbol), s.symbol)
    )


# ---------------------------------------------------------------------------
# market watch


# fetch_market_watch (imported above, tsetmc_api.market) gives the rows of
# the market watch (دیده بان بازار), one per instrument.
# Page: https://www.tsetmc.com/marketwatchnew, see
# tse_settings.MARKET_WATCH_URL


def market_symbols_from_market_watch(
    rows: Sequence[MarketWatchInstrument],
) -> List[MarketSymbol]:
    """Market symbols of market watch rows.

    Rows whose symbol ends with a number are skipped.
    """
    market_symbols = []
    for row in rows:
        symbol = clean_symbol(row.symbol or "")
        if not symbol or _ends_with_number(symbol):
            continue
        market_symbols.append(
            MarketSymbol(
                code=(row.isin or "").strip(),
                symbol=symbol,
                name=clean_name(row.name or ""),
                index=row.ins_code,
                old=[],
            )
        )
    return market_symbols


def get_market_symbols_from_market_watch_page() -> List[MarketSymbol]:
    """get symbols list from the market watch (دیده بان بازار)

    :return: list of market symbols
    :rtype: List[MarketSymbol]
    """
    return market_symbols_from_market_watch(fetch_market_watch())


# ---------------------------------------------------------------------------
# instruments missing from the market watch


def get_instrument_codes_from_closing_price_history() -> Set[str]:
    """insCodes of every instrument with a closing price in the last ~60
    trading days, including suspended ones the market watch does not show.
    """
    # Page: market watch filters, see CLOSING_PRICE_DAILY_ALL_INST_URL
    rows = fetch_closing_price_daily_all_inst(timeout=300)
    return {row.ins_code for row in rows if row.ins_code}


async def get_market_symbols_from_instrument_codes(
    ins_codes: Iterable[str],
    session: Optional[aiohttp.ClientSession] = None,
    concurrency: int = DEFAULT_CONCURRENCY,
) -> List[MarketSymbol]:
    """Market symbols of the given insCodes, read from the instrument info.

    Symbols that end with a number are skipped, like in the market watch.
    Instruments whose info can not be read are skipped with a warning.
    """
    semaphore = asyncio.Semaphore(concurrency)
    async with _client_session(session) as session:

        async def get_one(ins_code: str) -> Optional[MarketSymbol]:
            try:
                info = await _get_instrument_info(ins_code, session, semaphore)
            except Exception as ex:  # pylint: disable=broad-except
                logger.warning(
                    "cannot read instrument info of %s: %r", ins_code, ex
                )
                return None
            symbol = clean_symbol(info.symbol or "")
            if not symbol or _ends_with_number(symbol):
                return None
            return MarketSymbol(
                code=(info.isin or "").strip(),
                symbol=symbol,
                name=clean_name(info.name or ""),
                index=ins_code,
                old=[],
            )

        results = await asyncio.gather(
            *(get_one(code) for code in sorted(set(ins_codes)))
        )
    return [symbol for symbol in results if symbol is not None]


def load_market_symbols_from_json(
    path: Union[str, Path],
) -> List[MarketSymbol]:
    """Market symbols stored in a symbols_name.json file."""
    with open(path, "r", encoding="utf8") as file:
        data = json.load(file)
    return [
        MarketSymbol(
            code=value.get("code") or "",
            symbol=symbol,
            name=value.get("name") or "",
            index=str(value.get("index") or ""),
            old=[str(old) for old in value.get("old") or []],
        )
        for symbol, value in data.items()
    ]


# ---------------------------------------------------------------------------
# symbol search: active and old insCodes of a symbol


def match_search_results(
    results: Sequence[InstrumentSearchResult],
    symbol_name: str,
    preferred_index: Optional[str] = None,
) -> Tuple[Optional[InstrumentSearchResult], List[str]]:
    """Find the instruments of a symbol in the rows of a symbol search.

    The search returns instruments whose symbol or name contains the query;
    only the ones whose symbol is exactly ``symbol_name`` are used.

    Returns the search row of the active instrument (None when every
    instrument of the symbol is deleted) and the insCodes of the old,
    deleted instruments of the symbol. When more than one instrument is
    active, the one whose insCode is ``preferred_index`` wins if present.

    Note: the search returns at most ~40 rows, so old instruments of
    symbols that match many other symbols or names can be missing.
    """
    symbol_name = clean_symbol(symbol_name)
    active_rows = []
    old_ids = []
    for row in results:
        if clean_symbol(row.symbol or "") != symbol_name:
            continue
        # the website shows rows whose lastDate is 0 as
        # "(نماد قدیمی حذف شده)" (old deleted symbol)
        if row.is_deleted:
            old_ids.append(row.ins_code)
        else:
            active_rows.append(row)
    active = None
    if active_rows:
        active = next(
            (row for row in active_rows if row.ins_code == preferred_index),
            active_rows[0],
        )
    return active, _unique(old_ids)


def get_symbol_info(symbol_name: str) -> Optional[MarketSymbol]:
    """Look a symbol up on the API (for symbols missing from the JSON).

    Returns the active insCode (index), the ISIN (code, empty when it can
    not be read), the name and the old insCodes of the symbol, or None when
    no active instrument has exactly this symbol.

    Raises requests.RequestException when the search request fails.
    """
    symbol = clean_symbol(symbol_name)
    if not symbol:
        return None
    with requests_retry_session() as session:
        # Symbol search box (any page), see tse_settings.TSE_SYMBOL_ID_URL
        results = fetch_instrument_search(symbol, session=session)
        active, old_ids = match_search_results(results, symbol)
        if active is None:
            return None
        index = active.ins_code
        code = ""
        name = clean_name(active.name or "")
        try:
            # Instrument page https://www.tsetmc.com/instInfo/{insCode},
            # see tse_settings.TSE_INSTRUMENT_INFO
            info = fetch_instrument_info(index, session=session, timeout=30)
            code = (info.isin or "").strip()
            name = name or clean_name(info.name or "")
        except (requests.RequestException, KeyError, TypeError, ValueError):
            logger.warning("cannot read the ISIN of %s (%s)", symbol, index)
    return MarketSymbol(
        code=code,
        symbol=symbol,
        name=name,
        index=index,
        old=[old for old in old_ids if old != index],
    )


async def get_symbol_ids(
    symbol_name: str,
    session: aiohttp.ClientSession,
    semaphore: Optional[asyncio.Semaphore] = None,
) -> Tuple[Optional[str], List[str]]:
    """Active insCode of a symbol (None if all are deleted) and its old
    insCodes, from the symbol search."""
    results = await _search_symbol(symbol_name, session, semaphore)
    active, old_ids = match_search_results(results, symbol_name)
    return (active.ins_code if active else None), old_ids


async def add_old_indexes_to_market_symbols(
    symbols: List[MarketSymbol],
    active_symbols: Optional[Dict[str, str]] = None,
    previous: Optional[Dict[str, MarketSymbol]] = None,
    concurrency: int = DEFAULT_CONCURRENCY,
) -> List[MarketSymbol]:
    """
    Look every symbol up with the symbol search to find its active index
    and its old indexes. Symbols without an active instrument (deleted) are
    dropped.

    Parameters
    ----------
    symbols : List[MarketSymbol]
        list of market symbols (deduplicated).
    active_symbols : Dict[str, str]
        symbol to insCode of the symbols known to be active (the market
        watch); these keep their index even when the search does not list
        them (it does not find some energy exchange instruments).
    previous : Dict[str, MarketSymbol]
        symbols of the current symbols_name.json by symbol. Their old
        indexes are kept (the search returns at most ~40 rows and can miss
        some) and they are kept unchanged when the search request fails.
    concurrency : int
        number of requests sent at the same time.

    Returns
    -------
    List[MarketSymbol]
        list of market symbols.

    """
    active_symbols = active_symbols or {}
    previous = previous or {}
    semaphore = asyncio.Semaphore(concurrency)
    done = 0

    async with _client_session() as session:

        async def resolve(symbol: MarketSymbol) -> Optional[MarketSymbol]:
            nonlocal done
            try:
                return await _resolve_market_symbol(
                    symbol, session, semaphore, active_symbols, previous
                )
            except Exception as ex:  # pylint: disable=broad-except
                logger.warning("cannot look %s up: %r", symbol.symbol, ex)
                previous_symbol = previous.get(symbol.symbol)
                if active_symbols.get(symbol.symbol) != symbol.index:
                    return previous_symbol
                if previous_symbol is None:
                    return symbol
                # active in the market watch: keep the old indexes of the
                # json, the search could not be asked for them
                old = previous_symbol.old + [previous_symbol.index]
                return replace(
                    symbol,
                    old=[
                        i
                        for i in _unique(symbol.old + old)
                        if i != symbol.index
                    ],
                )
            finally:
                done += 1
                if done % 200 == 0:
                    logger.info("looked up %d/%d symbols", done, len(symbols))

        results = await asyncio.gather(*(resolve(s) for s in symbols))

    return remove_active_indexes_from_old(
        [symbol for symbol in results if symbol is not None]
    )


def remove_active_indexes_from_old(
    symbols: List[MarketSymbol],
) -> List[MarketSymbol]:
    """
    Remove from every old list the indexes that are active under another
    symbol.

    The old indexes of a symbol are read as part of its history, and
    Ticker(index=...) treats an index in any old list as deleted. A renamed
    instrument keeps its index under its new symbol (the fund once named
    سحرخیز is now سافرون, and سحرخیز is a new company), so that index must
    not stay in the old list of the previous symbol. A deleted symbol whose
    own index is active under another symbol was only renamed, it is kept
    as another name of that instrument.

    A symbol is active when its index is not in its own old list.
    """
    active = {
        symbol.index: symbol.symbol
        for symbol in symbols
        if symbol.index not in symbol.old
    }
    result = []
    for symbol in symbols:
        old = [
            index
            for index in symbol.old
            if active.get(index, symbol.symbol) == symbol.symbol
        ]
        if old != symbol.old:
            logger.info(
                "%s: removed old indexes active under another symbol: %s",
                symbol.symbol,
                [index for index in symbol.old if index not in old],
            )
            symbol = replace(symbol, old=old)
        result.append(symbol)
    return result


async def _resolve_market_symbol(
    symbol: MarketSymbol,
    session: aiohttp.ClientSession,
    semaphore: asyncio.Semaphore,
    active_symbols: Dict[str, str],
    previous: Dict[str, MarketSymbol],
) -> Optional[MarketSymbol]:
    results = await _search_symbol(symbol.symbol, session, semaphore)
    active, old_ids = match_search_results(
        results, symbol.symbol, preferred_index=symbol.index
    )
    if active_symbols.get(symbol.symbol) == symbol.index:
        index = symbol.index
        name = symbol.name
        if active is None or active.ins_code != index:
            logger.info(
                "search does not list %s (%s) as active, the market watch "
                "does",
                symbol.symbol,
                index,
            )
    elif active is not None:
        index = active.ins_code
        name = clean_name(active.name or "") or symbol.name
    else:
        logger.debug("%s is deleted", symbol.symbol)
        previous_symbol = previous.get(symbol.symbol)
        if previous_symbol is None:
            return None
        # keep deleted symbols that are already in the json so their
        # history can still be downloaded by symbol. Like before, their
        # index is also in their old list, Ticker uses that to know the
        # symbol is deleted (no realtime data).
        return MarketSymbol(
            code=previous_symbol.code,
            symbol=previous_symbol.symbol,
            name=previous_symbol.name,
            index=previous_symbol.index,
            old=_unique(
                old_ids + previous_symbol.old + [previous_symbol.index]
            ),
        )

    code = symbol.code if index == symbol.index else ""
    if not code:
        try:
            info = await _get_instrument_info(index, session, semaphore)
            code = (info.isin or "").strip()
        except Exception as ex:  # pylint: disable=broad-except
            logger.warning(
                "cannot read the ISIN of %s (%s): %r", symbol.symbol, index, ex
            )

    previous_symbol = previous.get(symbol.symbol)
    previous_ids = (
        previous_symbol.old + [previous_symbol.index]
        if previous_symbol is not None
        else []
    )
    old = [i for i in _unique(old_ids + previous_ids) if i != index]
    return MarketSymbol(
        code=code, symbol=symbol.symbol, name=name, index=index, old=old
    )


# ---------------------------------------------------------------------------
# async http helpers


@asynccontextmanager
async def _client_session(
    session: Optional[aiohttp.ClientSession] = None,
) -> AsyncIterator[aiohttp.ClientSession]:
    """Use the given aiohttp session or open (and close) a new one."""
    if session is not None:
        yield session
        return
    connector = aiohttp.TCPConnector(limit=DEFAULT_CONCURRENCY)
    async with aiohttp.ClientSession(
        headers=tse_settings.HEADERS, connector=connector
    ) as own_session:
        yield own_session


def _is_retryable(ex: BaseException) -> bool:
    if isinstance(ex, aiohttp.ClientResponseError):
        return ex.status == 429 or ex.status >= 500
    return isinstance(
        ex, (aiohttp.ClientError, asyncio.TimeoutError, json.JSONDecodeError)
    )


@retry(
    retry=retry_if_exception(_is_retryable),
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, max=30) + wait_random(0, 1),
    reraise=True,
)
async def _get_json_async(
    url: str,
    session: aiohttp.ClientSession,
    semaphore: Optional[asyncio.Semaphore] = None,
) -> Any:
    semaphore = semaphore or asyncio.Semaphore(1)
    timeout = aiohttp.ClientTimeout(total=_REQUEST_TIMEOUT)
    async with semaphore:
        async with session.get(
            URL(url, encoded=True),
            headers=tse_settings.HEADERS,
            timeout=timeout,
        ) as response:
            response.raise_for_status()
            return json.loads(await response.text())


async def _search_symbol(
    symbol_name: str,
    session: aiohttp.ClientSession,
    semaphore: Optional[asyncio.Semaphore] = None,
) -> List[InstrumentSearchResult]:
    # Symbol search box (any page), see tse_settings.TSE_SYMBOL_ID_URL
    return parse_instrument_search(
        await _get_json_async(
            instrument_search_url(symbol_name), session, semaphore
        )
    )


async def _get_instrument_info(
    ins_code: str,
    session: aiohttp.ClientSession,
    semaphore: Optional[asyncio.Semaphore] = None,
) -> InstrumentInfo:
    # Instrument page https://www.tsetmc.com/instInfo/{insCode},
    # see tse_settings.TSE_INSTRUMENT_INFO
    return parse_instrument_info(
        await _get_json_async(
            tse_settings.TSE_INSTRUMENT_INFO.format(ins_code),
            session,
            semaphore,
        )
    )
