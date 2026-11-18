import functools
from typing import Dict, List, Optional

import pandas as pd
from pytse_client import config, symbols_data, tse_settings
from pytse_client.download import download_financial_indexes
from pytse_client.tsetmc_api.index import (
    IndexIntraday,
    fetch_index_companies,
    fetch_index_intraday,
)
from pytse_client.utils import persian


class FinancialIndex:
    def __init__(
        self,
        symbol: str,
        index: Optional[str] = None,
        base_path: Optional[str] = config.FINANCIAL_INDEX_BASE_PATH,
        write_history: Optional[bool] = False,
    ):
        # names in indices_name.json use arabic letters (ي, ك)
        self._index: str = index or symbols_data.get_financial_index(
            persian.replace_persian(symbol)
        )
        self.symbol: str = (
            persian.replace_persian(symbol) if index is None else self._index
        )
        self._intraday_url = (
            tse_settings.FINANCIAL_INDEX_EXPORT_INTRADAY_URL.format(
                self._index
            )
        )
        self._base_path = base_path
        self._write_history = write_history

    @property
    def last_update(self) -> str:
        """
        زمان انتشار, time of the last published value as HH:MM
        """
        return self._last_intraday_row.time.strftime("%H:%M")

    @property
    def last_value(self) -> float:
        """
        آخرین مقدار شاخص
        """
        return self._last_intraday_row.value

    @property
    def high(self) -> float:
        """
        بیشترین مقدار روز
        """
        return self._last_intraday_row.high

    @property
    def low(self) -> float:
        """
        کمترین مقدار روز
        """
        return self._last_intraday_row.low

    @property
    @functools.lru_cache()
    def history(self):
        return download_financial_indexes(
            self.symbol,
            write_to_csv=self._write_history,
            include_jdate=True,
            base_path=self._base_path,
        )[self.symbol]

    def _get_contributing_symbols(self):
        """
        شرکت های موجود در شاخص
        """
        companies = fetch_index_companies(self._index).companies
        return [
            {
                "symbol": persian.replace_arabic(company.instrument.symbol),
                "index": company.ins_code,
            }
            for company in companies
        ]

    @property
    @functools.lru_cache()
    def contributing_symbols(self) -> List[Dict[str, str]]:
        return self._get_contributing_symbols()

    @property
    def intraday_price(self) -> pd.DataFrame:
        """
        سابقه شاخص روز جاری, values of the index in the last trading day
        columns: value, change_percentage, low, high, indexed by time
        """
        df = pd.DataFrame(
            [
                [
                    row.time,
                    row.value,
                    row.change_percent,
                    row.low,
                    row.high,
                ]
                for row in self._intraday_rows
            ],
            columns=["time", "value", "change_percentage", "low", "high"],
        )
        df = df.astype(
            {
                "value": float,
                "change_percentage": float,
                "low": float,
                "high": float,
            },
            errors="raise",
        )
        return df.set_index("time")

    @property
    def _intraday_rows(self) -> List[IndexIntraday]:
        rows = fetch_index_intraday(self._index, timeout=30)
        return sorted(rows, key=lambda row: row.time)

    @property
    def _last_intraday_row(self) -> IndexIntraday:
        rows = self._intraday_rows
        if not rows:
            raise RuntimeError(
                f"no intraday data for financial index {self.symbol}"
            )
        return rows[-1]
