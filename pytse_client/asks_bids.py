import os
from pathlib import Path

import pandas as pd
from pytse_client import utils
from pytse_client.config import ASKS_BIDS_PATH
from pytse_client.ticker_statisticals import get_keys_of_asks_bids
from pytse_client.tsetmc_api.market import fetch_market_watch

keys_of_asks_bids = get_keys_of_asks_bids()


def get_asks_and_bids(to_csv=False, base_path=None):
    market_watch = fetch_market_watch(timeout=120)
    # one row per instrument and order book level (best 5 levels); prices
    # are float64 columns like before
    ticker_ls = [
        {
            "id": instrument.ins_code,
            "row_number": level.level,
            "num_of_sellers": level.sell_count,
            "number_of_buyers": level.buy_count,
            "buy_price": float(level.buy_price),
            "sell_price": float(level.sell_price),
            "buy_volume": level.buy_volume,
            "sell_volume": level.sell_volume,
        }
        for instrument in market_watch
        for level in instrument.best_limits
    ]

    df = pd.DataFrame(ticker_ls, columns=keys_of_asks_bids)
    index_to_symbols_map = utils.map_index_to_symbols()

    # filter df only if id is in index_to_symbols_map
    df = df[df["id"].isin(index_to_symbols_map.keys())]
    # create symbol based on map
    df["symbol"] = df["id"].map(
        lambda id: index_to_symbols_map.get(id)["symbol"]
    )

    if to_csv:
        base_path = base_path or ASKS_BIDS_PATH
        Path(base_path).mkdir(parents=True, exist_ok=True)

        path = os.path.join(base_path, "bids_asks.csv")
        df.to_csv(path, index=False)

    return df
