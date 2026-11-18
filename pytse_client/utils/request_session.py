from typing import Any, Optional

import requests
from pytse_client import tse_settings
from requests.adapters import HTTPAdapter
from urllib3 import Retry


def requests_retry_session(
    retries=5,
    backoff_factor=0.3,
    status_forcelist=(500, 502, 504, 503),
    session=None,
) -> requests.Session:
    session = session or requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update(tse_settings.HEADERS)
    return session


def get_json(
    url: str,
    session: Optional[requests.Session] = None,
    timeout: float = 30,
) -> Any:
    """GET a TSETMC API url and return the decoded JSON body.

    Uses the given session, or a new retrying session that is closed
    afterwards. Raises requests.HTTPError on an error status.
    """
    own_session = session is None
    session = session or requests_retry_session()
    try:
        response = session.get(
            url, headers=tse_settings.HEADERS, timeout=timeout
        )
        response.raise_for_status()
        return response.json()
    finally:
        if own_session:
            session.close()
