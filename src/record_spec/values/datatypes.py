"""The datatype registry: which comparators apply to which XSD datatypes."""

from __future__ import annotations

from typing import Any

from .comparator import (
    Comparator,
    _parse_boolean,
    _parse_datetime,
    _parse_decimal,
    _parse_float,
    _parse_int,
)

XSD = "http://www.w3.org/2001/XMLSchema#"
RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
RDF_LANG_STRING = RDF + "langString"

_STRING_COMPARATOR = Comparator[str](lambda s: s)


class Datatype:
    """A registered datatype with its value comparator."""

    def __init__(self, comparator: Comparator[Any]):
        self.comparator = comparator


_STRING = Datatype(_STRING_COMPARATOR)
_INT = Datatype(Comparator(_parse_int))
_FLOAT = Datatype(Comparator(_parse_float))
_DECIMAL = Datatype(Comparator(_parse_decimal))
_BOOLEAN = Datatype(Comparator(_parse_boolean))
_DATETIME = Datatype(Comparator(_parse_datetime))


class Datatypes:
    """The registry of known datatypes and their comparators."""

    register: dict[str, Datatype] = {}

    @classmethod
    def _populate(cls) -> None:
        register = cls.register
        register[XSD + "date"] = _DATETIME
        register[XSD + "dateTime"] = _DATETIME
        register[XSD + "boolean"] = _BOOLEAN
        register[XSD + "float"] = _FLOAT
        register[XSD + "double"] = _FLOAT
        register[XSD + "decimal"] = _DECIMAL
        register[XSD + "integer"] = _INT
        register[XSD + "nonPositiveInteger"] = _INT
        register[XSD + "negativeInteger"] = _INT
        register[XSD + "nonNegativeInteger"] = _INT
        register[XSD + "long"] = _INT
        register[XSD + "int"] = _INT
        register[XSD + "string"] = _STRING
        register[XSD + "anyURI"] = _STRING


Datatypes._populate()

__all__ = [
    "XSD",
    "RDF",
    "RDF_LANG_STRING",
    "Comparator",
    "Datatype",
    "Datatypes",
]