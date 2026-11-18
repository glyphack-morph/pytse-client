import datetime
import json
import logging
import multiprocessing
from typing import Dict, List, Optional

import pandas as pd
from pytse_client.config import LOGGER_NAME
from pytse_client.orderbook.common import (
    ORDERBOOK_HEADER,
    best_limits_history_frame,
    common_process,
    get_valid_dates,
    process_diff_orderbook,
    validate_dates,
    write_to_csv,
)
from pytse_client.orderbook.order_book_async import get_df_valid_dates
from pytse_client.ticker.ticker import Ticker
from pytse_client.tse_settings import TICKER_ORDER_BOOK
from pytse_client.tsetmc_api.best_limits import parse_best_limits_history
from pytse_client.utils.logging_generator import get_logger
from pytse_client.utils.request_session import requests_retry_session

logger = get_logger(f"{LOGGER_NAME}_orderbook", logging.INFO)


def get_orderbook(
    symbol_name: str,
    start_date: datetime.date,
    end_date: Optional[datetime.date] = None,
    to_csv: bool = False,
    base_path: Optional[str] = None,
    ignore_date_validation: bool = False,
    diff_orderbook: bool = False,  # faster to process but only stores the difference
    async_requests: bool = True,
) -> Dict[str, pd.DataFrame]:
    end_date = start_date if not end_date else end_date
    ticker = Ticker(symbol_name)

    validate_dates(ticker, start_date, end_date, ignore_date_validation)
    all_valid_dates = get_valid_dates(ticker, start_date, end_date)

    date_df_list = []
    if async_requests:
        date_df_list.extend(get_df_valid_dates(ticker, all_valid_dates))
    else:
        for valid_date in all_valid_dates:
            df = _get_diff_orderbook(ticker, valid_date)
            date_df_list.append([valid_date, df])

    pool = multiprocessing.Pool(processes=multiprocessing.cpu_count())
    args_list: List[Dict] = []
    for date_df in date_df_list:
        date, df = date_df
        args_list.append(
            {
                "df": df,
                "date": date,
                "to_csv": to_csv,
                "base_path": base_path,
                "diff_orderbook": diff_orderbook,
            }
        )

    result = {}
    with pool as p:
        df_list = p.map(_get_orderbook_wrapper, args_list)
    for idx, df in enumerate(df_list):
        date = args_list[idx]["date"]
        result[date.strftime("%Y-%m-%d")] = df

    return result


def _get_orderbook_wrapper(args: dict):
    df, date, to_csv, base_path, diff_orderbook = (
        args["df"],
        args["date"],
        args["to_csv"],
        args["base_path"],
        args["diff_orderbook"],
    )
    return _get_orderbook(df, date, to_csv, base_path, diff_orderbook)


def _get_orderbook(
    df: pd.DataFrame,
    date: datetime.date,
    to_csv=False,
    base_path=None,
    diff_orderbook=False,
):
    newdf = common_process(df, date.strftime("%Y%m%d"))
    if not diff_orderbook:
        newdf = process_diff_orderbook(newdf)
    if to_csv:
        write_to_csv(newdf, base_path, date)
    logger.info(f"successfully construct orderbook on {date}")
    return newdf


def _get_diff_orderbook(ticker: Ticker, date_obj: datetime.date):
    index = ticker.index
    date = date_obj.strftime("%Y%m%d")
    session = requests_retry_session(retries=5, backoff_factor=0.2)
    url = TICKER_ORDER_BOOK.format(index=index, date=date)

    try:
        response = session.get(url, headers=ORDERBOOK_HEADER, timeout=10)
        response.raise_for_status()
    finally:
        session.close()
    logger.info(f"successfully download raw orderbook on {date_obj} from tse")
    data = json.loads(response.content)

    return best_limits_history_frame(parse_best_limits_history(data))
