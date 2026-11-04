"""Model value types shared across the schema model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LangString:
    """A language-tagged string."""

    value: str
    language: str | None = None


@dataclass(frozen=True)
class PrefixMapping:
    """A mapping of a prefix string to a URI."""

    prefix: str
    uri: str