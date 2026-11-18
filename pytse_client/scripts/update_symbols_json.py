"""Regenerate pytse_client/data/symbols_name.json from the TSETMC API.

Run from the repository root:

    python -m pytse_client.scripts.update_symbols_json

See pytse_client/scraper/symbol_scraper.py for where the symbols come from.
Sorting uses the fa_IR collation; generate the locale if it is missing
(sudo localedef -i fa_IR -f UTF-8 fa_IR.UTF-8), otherwise a simple Persian
alphabet order is used.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import List

from pytse_client import config
from pytse_client.scraper.symbol_scraper import (
    DEFAULT_CONCURRENCY,
    MarketSymbol,
    add_old_indexes_to_market_symbols,
    deduplicate_market_symbols,
    fetch_market_watch,
    get_instrument_codes_from_closing_price_history,
    get_market_symbols_from_instrument_codes,
    load_market_symbols_from_json,
    market_symbols_from_market_watch,
    set_persian_collation,
    sort_market_symbols,
)

SYMBOLS_FILE_NAME = "symbols_name.json"


def write_symbols_to_json(
    market_symbols: List[MarketSymbol], filename: str, path: str
) -> None:
    Path(path).mkdir(parents=True, exist_ok=True)
    with open(f"{path}/{filename}", "w", encoding="utf8") as file:
        data = {
            obj.symbol: {
                "index": obj.index,
                "code": obj.code,
                "name": obj.name,
                "old": obj.old,
            }
            for obj in market_symbols
        }
        json.dump(data, file, ensure_ascii=False, indent=2)


async def main(concurrency: int = DEFAULT_CONCURRENCY):
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    set_persian_collation()
    data_dir = f"{config.pytse_dir}/data"
    json_path = Path(data_dir) / SYMBOLS_FILE_NAME

    previous: List[MarketSymbol] = []
    if json_path.exists():
        previous = load_market_symbols_from_json(json_path)
    print(f"symbols in the current {SYMBOLS_FILE_NAME}: {len(previous)}")

    market_watch_rows = fetch_market_watch()
    market_watch_codes = {row.ins_code for row in market_watch_rows}
    market_watch_symbols = market_symbols_from_market_watch(market_watch_rows)
    print(
        f"market watch: {len(market_watch_rows)} instruments, "
        f"{len(market_watch_symbols)} symbols"
    )

    # instruments that are not in the market watch (mostly suspended ones),
    # their symbols are read from the instrument info
    history_codes = get_instrument_codes_from_closing_price_history()
    missing_codes = history_codes - market_watch_codes
    history_symbols = await get_market_symbols_from_instrument_codes(
        missing_codes, concurrency=concurrency
    )
    print(
        f"closing price history: {len(history_codes)} instruments, "
        f"{len(missing_codes)} not in the market watch, "
        f"{len(history_symbols)} symbols"
    )

    # the order is important, the first source of a symbol wins
    # https://github.com/Glyphack/pytse-client/issues/123
    market_symbols = deduplicate_market_symbols(
        market_watch_symbols + history_symbols + previous
    )
    print(f"Total deduplicated symbols: {len(market_symbols)}")

    # find the active and old indexes of every symbol, drop deleted ones
    market_symbols = await add_old_indexes_to_market_symbols(
        market_symbols,
        active_symbols={s.symbol: s.index for s in market_watch_symbols},
        previous={symbol.symbol: symbol for symbol in previous},
        concurrency=concurrency,
    )
    print(f"finished fetching old indexes, symbols: {len(market_symbols)}")

    write_symbols_to_json(
        sort_market_symbols(market_symbols), SYMBOLS_FILE_NAME, data_dir
    )


if __name__ == "__main__":
    asyncio.run(main())
