"""Datatype comparators used to order and merge literal value constraints."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Generic, Protocol, TypeVar


class SupportsComparison(Protocol):
    def __lt__(self, other: Any) -> bool: ...
    def __gt__(self, other: Any) -> bool: ...


T = TypeVar("T", bound=SupportsComparison)


def _parse_int(value: str) -> int:
    return int(value.strip())


def _parse_float(value: str) -> float:
    return float(value.strip())


def _parse_decimal(value: str) -> Decimal:
    try:
        return Decimal(value.strip())
    except InvalidOperation as e:
        raise ValueError(f"Invalid decimal value: {value!r}") from e


def _parse_boolean(value: str) -> bool:
    """Parse an XSD-style boolean.

    Mirrors the lenient Kotlin ``String.toBoolean``: "true" (any case) is true,
    anything else is false.
    """
    return value.strip().lower() == "true"


def _parse_datetime(value: str) -> datetime:
    """Parse an ``xsd:date`` or ``xsd:dateTime`` value into a comparable datetime.

    Dates without a time component are normalized to midnight so that they can
    be compared with date-times, matching the Kotlin behaviour of converting
    both to an instant.
    """
    text = value.strip()
    if "T" in text or " " in text:
        try:
            return datetime.fromisoformat(text)
        except ValueError:
            # Re-try with a fixed "Z" → "+00:00" for older forms
            return datetime.fromisoformat(text[:-1] + "+00:00") if text.endswith("Z") else datetime.fromisoformat(text)
    return datetime.combine(date.fromisoformat(text), datetime.min.time())


class Comparator(Generic[T]):
    """A comparator that parses string values into a comparable type."""

    def __init__(self, parse: Callable[[str], T]):
        self.parse = parse

    def compare(self, value_a: str, value_b: str) -> int:
        """Compare two string values, returning a negative/zero/positive int."""
        a = self.parse(value_a)
        b = self.parse(value_b)
        return (a > b) - (a < b)

    def min(self, value_a: str | None, value_b: str | None) -> str | None:
        """Return the smaller of two optional string values, preserving the original string."""
        if value_a is None:
            return value_b
        if value_b is None:
            return value_a
        return value_b if self.parse(value_b) < self.parse(value_a) else value_a

    def max(self, value_a: str | None, value_b: str | None) -> str | None:
        """Return the larger of two optional string values, preserving the original string."""
        if value_a is None:
            return value_b
        if value_b is None:
            return value_a
        return value_b if self.parse(value_b) > self.parse(value_a) else value_a