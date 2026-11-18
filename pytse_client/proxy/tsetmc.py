import datetime
import logging
from typing import List

import aiohttp
from pytse_client import config, tse_settings
from pytse_client.tsetmc_api.instrument import (
    InstrumentHistory,
    parse_instrument_history,
)
from pytse_client.tsetmc_api.shareholder import (
    Shareholder,
    parse_day_shareholders,
)
from tenacity import retry
from tenacity.before_sleep import before_sleep_log
from tenacity.stop import stop_after_attempt
from tenacity.wait import wait_random

logger = logging.getLogger(config.LOGGER_NAME)


@retry(
    wait=wait_random(min=3, max=5),
    # without a limit a day that always fails would hang the caller
    stop=stop_after_attempt(10),
    reraise=True,
    before_sleep=before_sleep_log(logger, logging.ERROR),
)
async def get_day_shareholders_history(
    ticker_index: str,
    date: datetime.date,
    session: aiohttp.ClientSession,
) -> List[Shareholder]:
    """Major shareholders of an instrument before the session of a day,
    see tsetmc_api.shareholder."""
    formatted_date = date.strftime(tse_settings.DATE_FORMAT)
    async with session.get(
        tse_settings.SYMBOL_DAY_INFO_SHAREHOLDERS_DATA.format(
            index=ticker_index, date=formatted_date
        ),
    ) as response:
        response.raise_for_status()
        response_json = await response.json()
        logger.debug(
            "fetched shareholders data for%s date: %s",
            ticker_index,
            formatted_date,
        )
        # api returns data for today and tomorrow so we skip tomorrow
        # sometimes when we request data for a day it returns it with
        # tomorrow date instead(bug) so we only check that the
        # date is greater than requested date. date can be a datetime.
        day = datetime.date(date.year, date.month, date.day)
        return [
            shareholder
            for shareholder in parse_day_shareholders(response_json)
            if shareholder.date is None or shareholder.date <= day
        ]


@retry(
    # These numbers are not tested
    wait=wait_random(min=3, max=5),
    stop=stop_after_attempt(10),
    reraise=True,
    before_sleep=before_sleep_log(logger, logging.ERROR),
)
async def get_day_ticker_info_history(
    ticker_index: str,
    date: datetime.date,
    session: aiohttp.ClientSession,
) -> InstrumentHistory:
    """

    Args:
        ticker_index
        date
        session: aiohttp sesison to reuse session will be closed after usage

    Returns: InstrumentHistory, see tsetmc_api.instrument
    """
    formatted_date = date.strftime(tse_settings.DATE_FORMAT)
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-GB,en;q=0.5",
        "Connection": "keep-alive",
        "Referer": (
            f"https://www.tsetmc.com/History/{ticker_index}/{formatted_date}"
        ),
        "Sec-GPC": "1",
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 9) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.5112.102"
            "Safari/537.36"
        ),
    }
    async with session.get(
        tse_settings.SYMBOL_DAY_INSTRUMENT_INFO_URL.format(
            index=ticker_index, date=formatted_date
        ),
        headers=headers,
    ) as response:
        response.raise_for_status()
        response_json = await response.json()
        logger.debug(
            "fetched instrument info %s date: %s",
            ticker_index,
            formatted_date,
        )
        return parse_instrument_history(response_json)
