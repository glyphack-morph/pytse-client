"""Responses of the History page endpoints, defined in
pytse_client.tsetmc_api; the old names are kept importable from here.

ShareholderData is a row of Shareholder/{insCode}/{date}
(tsetmc_api.shareholder.Shareholder), InstrumentHistoryResponse the answer
of Instrument/GetInstrumentHistory/{insCode}/{date}
(tsetmc_api.instrument.InstrumentHistory, total_shares and base_volume
first like before).
"""

from pytse_client.tsetmc_api.instrument import InstrumentHistory
from pytse_client.tsetmc_api.shareholder import Shareholder

__all__ = ["InstrumentHistoryResponse", "ShareholderData"]

ShareholderData = Shareholder
InstrumentHistoryResponse = InstrumentHistory
