"""Conversions shared by the parse functions of the TSETMC API.

The API sends dates as Gregorian YYYYMMDD ints (dEven, 20261116), times
as HHMMSS ints (hEven, 90017 for 09:00:17), and most counts, prices and
volumes as floats with no fraction (5120.0). The parse functions turn them
into date, time and int.
"""

import datetime
from functools import lru_cache
from typing import Any, Optional


@lru_cache(maxsize=8192)
def to_date(d_even: int) -> datetime.date:
    """dEven (YYYYMMDD, e.g. 20261116) to a date."""
    d_even = int(d_even)
    return datetime.date(d_even // 10000, d_even // 100 % 100, d_even % 100)


def to_optional_date(d_even: Optional[int]) -> Optional[datetime.date]:
    """Like to_date, but None when the API sends 0 or null (no date)."""
    if not d_even:
        return None
    return to_date(d_even)


@lru_cache(maxsize=65536)
def to_time(h_even: int) -> datetime.time:
    """hEven (HHMMSS, e.g. 90017) to a time (09:00:17)."""
    h_even = int(h_even)
    return datetime.time(h_even // 10000, h_even // 100 % 100, h_even % 100)


def to_optional_time(h_even: Optional[int]) -> Optional[datetime.time]:
    """Like to_time, but None when the API sends null."""
    if h_even is None:
        return None
    return to_time(h_even)


def to_heven(time: datetime.time) -> int:
    """A time back to the hEven int of the API (09:00:17 is 90017)."""
    return time.hour * 10000 + time.minute * 100 + time.second


def to_optional_int(value: Any) -> Optional[int]:
    """int of a number, None when the API sends null."""
    if value is None:
        return None
    return int(value)


def to_optional_float(value: Any) -> Optional[float]:
    """float of a number, None when the API sends null."""
    if value is None:
        return None
    return float(value)


def to_optional_bool(value: Any) -> Optional[bool]:
    """bool of a flag (true/false or 1/0), None when the API sends null."""
    if value is None:
        return None
    return bool(value)


def to_optional_str(value: Any) -> Optional[str]:
    """str of a code that the API sends as a string or a number."""
    if value is None:
        return None
    return str(value)


def number_text_to_float(value: Any) -> Optional[float]:
    """float of a number the API sends as text, e.g. "693" or "1,250".

    None when it is null, empty or not a number, like the website, which
    shows nothing for such values.
    """
    if value is None or value == "":
        return None
    try:
        return float(str(value).replace(",", ""))
    except ValueError:
        return None


def number_text_to_int(value: Any) -> Optional[int]:
    """int of a whole number the API sends as text, e.g. "1935000000".

    None when it is null, empty or not a number.
    """
    number = number_text_to_float(value)
    return int(number) if number is not None else None
