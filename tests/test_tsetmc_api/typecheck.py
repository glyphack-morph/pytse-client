"""Check that the fields of a parsed response have their annotated types.

Used by the live tests of pytse_client.tsetmc_api: every test fetches an
endpoint, parses it and calls assert_field_types on the result.
"""

import dataclasses
import datetime
import types
import typing
import unittest

# instruments and day used by the live tests
FOLAD = "46348559193224090"  # فولاد
TOTAL_INDEX = "32097828799138957"  # شاخص کل
FUND = "69067576215760005"  # fund کاریس
# a past trading day, for the endpoints of the History page
HISTORY_DAY = datetime.date(2026, 11, 16)

# the rows of large lists that are checked
_MAX_CHECKED_ROWS = 2000


def _matches(value, hint) -> bool:
    if hint is typing.Any:
        return True
    if hint is type(None):
        return value is None
    origin = typing.get_origin(hint)
    if origin in (typing.Union, types.UnionType):
        return any(_matches(value, arg) for arg in typing.get_args(hint))
    if origin is list:
        (item_hint,) = typing.get_args(hint)
        return isinstance(value, list) and all(
            _matches(item, item_hint) for item in _sample(value)
        )
    # bool is an int and datetime a date in python, they are not here
    if hint is int:
        return isinstance(value, int) and not isinstance(value, bool)
    if hint is float:
        return isinstance(value, float)
    if hint is datetime.date:
        return isinstance(value, datetime.date) and not isinstance(
            value, datetime.datetime
        )
    return isinstance(value, hint)


def _sample(rows: list) -> list:
    if len(rows) <= _MAX_CHECKED_ROWS:
        return rows
    return rows[:: len(rows) // _MAX_CHECKED_ROWS]


def assert_field_types(
    test: unittest.TestCase, value, path: typing.Optional[str] = None
) -> None:
    """Assert that every field of a dataclass (or of every dataclass in a
    list, nested ones included) has the type of its annotation."""
    if isinstance(value, list):
        for i, item in enumerate(_sample(value)):
            assert_field_types(test, item, f"{path or 'rows'}[{i}]")
        return
    test.assertTrue(
        dataclasses.is_dataclass(value), f"{path}: {value!r} is no dataclass"
    )
    path = path or type(value).__name__
    hints = typing.get_type_hints(type(value))
    for field in dataclasses.fields(value):
        field_value = getattr(value, field.name)
        hint = hints[field.name]
        test.assertTrue(
            _matches(field_value, hint),
            f"{path}.{field.name} = {field_value!r} is not {hint}",
        )
        if dataclasses.is_dataclass(field_value) or (
            isinstance(field_value, list)
            and field_value
            and dataclasses.is_dataclass(field_value[0])
        ):
            assert_field_types(test, field_value, f"{path}.{field.name}")
