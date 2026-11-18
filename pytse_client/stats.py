import os
from pathlib import Path
from typing import Dict, List

import pandas as pd
from pytse_client import config, utils
from pytse_client.ticker_statisticals import (
    filter_key_value,
    filter_value_NONE,
)
from pytse_client.ticker_statisticals.utils import (
    get_keys_of_client_types,
    get_keys_of_market_watch,
)
from pytse_client.tsetmc_api._convert import to_heven
from pytse_client.tsetmc_api.client_type import (
    ClientType,
    fetch_client_type_all,
)
from pytse_client.tsetmc_api.market import (
    InstrumentStatistic,
    MarketWatchInstrument,
    fetch_key_stats,
    fetch_market_watch,
)
from pytse_client.utils import map_index_to_symbols


def _get_dict_of_key_stats(
    key_stats_rows: List[InstrumentStatistic],
) -> Dict[str, Dict]:
    """
    output: {index: {key stat name: value}}, see
    ticker_statisticals/key_stats.py for the names of the stats
    """
    key_stats: Dict[str, Dict] = {}
    for row in key_stats_rows:
        key_name = filter_key_value.get(row.stat_id)
        # skip statistics this package does not know about
        if key_name is None:
            continue
        key_stats.setdefault(row.ins_code, {})[key_name] = row.value
    return key_stats


def _get_dict_of_client_types(client_types: List[ClientType]):
    """
    output: Dictionary of client types with the following keys:
        "index", "numof_individual_buy", "numof_corporate_buy",
        "vol_individual_buy", "vol_corporate_buy",
        "numof_individual_sell", "numof_corporate_sell",
        "vol_individual_sell", "vol_corporate_sell"
    """
    # volumes are floats like the api sends them, see get_stats
    return {
        row.ins_code: {
            "index": row.ins_code,
            "numof_individual_buy": row.individual_buy_count,
            "numof_corporate_buy": row.corporate_buy_count,
            "vol_individual_buy": float(row.individual_buy_volume),
            "vol_corporate_buy": float(row.corporate_buy_volume),
            "numof_individual_sell": row.individual_sell_count,
            "numof_corporate_sell": row.corporate_sell_count,
            "vol_individual_sell": float(row.individual_sell_volume),
            "vol_corporate_sell": float(row.corporate_sell_volume),
        }
        for row in client_types
    }


def _get_dict_of_market_watch(market_watch: List[MarketWatchInstrument]):
    """
    output: Dictionary of market watch with the following keys:
        "index", "code", "symbol", "name", "last_changed", "open_price",
        "adj_closing_price", "last_price", "number_of_trans",
        "volume_of_trans", "value_of_trans", "min_price", "max_price",
        "yesterday_price", "EPS", "base_volume", "visit_count", "flow",
        "group_number", "max_price_allowed", "min_price_allowed",
        "number_of_stocks", "yval"
    """
    # numbers keep the type the api sends them with (float, or int for
    # last_changed, visit_count, flow, min_price_allowed and yval): the
    # dtypes of the get_stats columns follow them
    return {
        row.ins_code: {
            "index": row.ins_code,
            "code": _strip(row.isin),
            "symbol": _strip(row.symbol),
            "name": _strip(row.name),
            "last_changed": to_heven(row.time),
            "open_price": float(row.first_price),
            "adj_closing_price": float(row.closing_price),
            "last_price": float(row.last_price),
            "number_of_trans": float(row.trade_count),
            "volume_of_trans": float(row.volume),
            "value_of_trans": float(row.value),
            "min_price": float(row.low_price),
            "max_price": float(row.high_price),
            "yesterday_price": float(row.yesterday_price),
            "EPS": row.eps,
            "base_volume": float(row.base_volume),
            "visit_count": row.visit_count,
            "flow": row.flow,
            "group_number": _strip(row.sector_code),
            "max_price_allowed": float(row.max_allowed_price),
            "min_price_allowed": row.min_allowed_price,
            "number_of_stocks": float(row.total_shares),
            "yval": row.instrument_type,
        }
        for row in market_watch
    }


def _strip(text):
    return text.strip() if isinstance(text, str) else text


def get_stats(base_path=None, to_csv=False) -> pd.DataFrame:
    aggregated_key_stats = {}
    index_to_symbol_map = map_index_to_symbols()
    session = utils.requests_retry_session()
    try:
        key_stats_dict = _get_dict_of_key_stats(_get_key_stats(session))
        client_types_dict = _get_dict_of_client_types(
            _get_client_types(session)
        )
        market_watch_dict = _get_dict_of_market_watch(
            _get_market_watch(session)
        )
    finally:
        session.close()

    for idx_stat, filter_key_found in key_stats_dict.items():
        if idx_stat not in index_to_symbol_map:
            continue
        else:
            symbol = index_to_symbol_map[idx_stat]["symbol"]
            name = index_to_symbol_map[idx_stat]["name"]

        client_types = client_types_dict.get(
            idx_stat, {key: None for key in get_keys_of_client_types()}
        )

        market_watch = market_watch_dict.get(
            idx_stat,
            {
                key: None
                for key in get_keys_of_market_watch()
                if key != "NOT_VALID_KEY"
            },
        )

        aggregated_key_stats[idx_stat] = {
            **filter_value_NONE,
            **filter_key_found,
            **client_types,
            **market_watch,
            "symbol": symbol,
            "name": name,
        }

    aggregated_key_stats_df = pd.DataFrame.from_dict(aggregated_key_stats).T

    # change type of columns to int
    str_cols = {"symbol", "name"}
    numeric_cols = set(aggregated_key_stats_df.columns) - str_cols
    numeric_cols_ls = list(numeric_cols)
    aggregated_key_stats_df[numeric_cols_ls] = aggregated_key_stats_df[
        numeric_cols_ls
    ].apply(pd.to_numeric, errors="coerce")
    aggregated_key_stats_df["index"] = aggregated_key_stats_df.index
    aggregated_key_stats_df = aggregated_key_stats_df.reset_index(drop=True)

    if to_csv:
        base_path = config.STATS_BASE_PATH if base_path is None else base_path
        Path(base_path).mkdir(parents=True, exist_ok=True)
        path = os.path.join(base_path, "key_stats.csv")
        print(path)
        aggregated_key_stats_df.to_csv(path, index=False)

    return aggregated_key_stats_df


def _get_key_stats(session) -> List[InstrumentStatistic]:
    try:
        return fetch_key_stats(session=session, timeout=180)
    except Exception as e:
        raise Exception(f"Failed to get key stats: {e}")


def _get_client_types(session) -> List[ClientType]:
    try:
        return fetch_client_type_all(session=session, timeout=120)
    except Exception as e:
        raise Exception(f"Failed to get client types: {e}")


def _get_market_watch(session) -> List[MarketWatchInstrument]:
    try:
        return fetch_market_watch(session=session, timeout=120)
    except Exception as e:
        raise Exception(f"Failed to get market watch: {e}")
