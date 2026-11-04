"""Read-side adapter interfaces.

`SchemaBuilder` consumes a :class:`SchemaAdapter` to build a :class:`Schema`.
Each source format (YAML/JSON def-tree, RDF, ...) provides its own
implementation of these interfaces.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterable

    from record_spec.model.property import PropertyKind
    from record_spec.model.values import LangString, PrefixMapping


class SchemaAdapter(ABC):
    """The read-side interface to a complete schema."""

    @property
    @abstractmethod
    def identifier(self) -> str | None: ...

    @property
    @abstractmethod
    def base_uri(self) -> str | None: ...

    @property
    @abstractmethod
    def label(self) -> Iterable[LangString]: ...

    @property
    @abstractmethod
    def summary(self) -> Iterable[LangString]: ...

    @property
    @abstractmethod
    def description(self) -> Iterable[LangString]: ...

    @property
    @abstractmethod
    def mixins(self) -> Iterable[MixinAdapter]: ...

    @property
    @abstractmethod
    def records(self) -> Iterable[RecordAdapter]: ...

    @property
    @abstractmethod
    def prefixes(self) -> Iterable[PrefixMapping]: ...

    @property
    @abstractmethod
    def imports(self) -> Iterable[str]: ...

    @property
    @abstractmethod
    def extensions(self) -> Iterable[dict[str, Any]]: ...


class RecordAdapter(ABC):
    """The read-side interface to a record definition."""

    @property
    @abstractmethod
    def id(self) -> str:
        """The IRI identifier for the record as a full (not compact) IRI."""

    @property
    @abstractmethod
    def class_uri(self) -> str:
        """The IRI identifier of the class of record instances as a full IRI."""

    @property
    @abstractmethod
    def short_code(self) -> str: ...

    @property
    @abstractmethod
    def label(self) -> Iterable[LangString]: ...

    @property
    @abstractmethod
    def summary(self) -> Iterable[LangString]: ...

    @property
    @abstractmethod
    def description(self) -> Iterable[LangString]: ...

    @property
    @abstractmethod
    def extends(self) -> str | None:
        """The short-code (or id) of the record that this record extends, if any."""

    @property
    @abstractmethod
    def mixins(self) -> Iterable[str]:
        """The ids of the mixins that this record implements."""

    @property
    @abstractmethod
    def properties(self) -> Iterable[PropertyAdapter]:
        """The properties that this record directly declares."""

    @property
    @abstractmethod
    def extensions(self) -> Iterable[dict[str, Any]]: ...


class MixinAdapter(ABC):
    """The read-side interface to a mixin definition."""

    @property
    @abstractmethod
    def id(self) -> str: ...

    @property
    @abstractmethod
    def label(self) -> Iterable[LangString]: ...

    @property
    @abstractmethod
    def summary(self) -> Iterable[LangString]: ...

    @property
    @abstractmethod
    def description(self) -> Iterable[LangString]: ...

    @property
    @abstractmethod
    def properties(self) -> Iterable[PropertyAdapter]: ...

    @property
    @abstractmethod
    def extensions(self) -> Iterable[dict[str, Any]]: ...


class PropertyAdapter(ABC):
    """The read-side interface to a property definition."""

    @property
    @abstractmethod
    def short_code(self) -> str: ...

    @property
    @abstractmethod
    def property_uri(self) -> str: ...

    @property
    @abstractmethod
    def label(self) -> Iterable[LangString]: ...

    @property
    @abstractmethod
    def summary(self) -> Iterable[LangString]: ...

    @property
    @abstractmethod
    def description(self) -> Iterable[LangString]: ...

    @property
    @abstractmethod
    def required(self) -> bool: ...

    @property
    @abstractmethod
    def repeatable(self) -> bool: ...

    @property
    @abstractmethod
    def kind(self) -> PropertyKind: ...

    @property
    @abstractmethod
    def nested(self) -> bool | None: ...

    @property
    @abstractmethod
    def reversed(self) -> bool | None: ...

    @property
    @abstractmethod
    def literal_constraints(self) -> Iterable[LiteralConstraintAdapter]: ...

    @property
    @abstractmethod
    def record_constraints(self) -> Iterable[RecordConstraintAdapter]: ...

    @property
    @abstractmethod
    def property_map(self) -> PropertyMappingAdapter | None: ...

    @property
    @abstractmethod
    def extensions(self) -> Iterable[dict[str, Any]]: ...


class LiteralConstraintAdapter(ABC):
    """The read-side interface to a literal constraint."""

    @property
    @abstractmethod
    def datatype(self) -> str: ...

    @property
    @abstractmethod
    def pattern(self) -> str | None: ...

    @property
    @abstractmethod
    def min_inclusive(self) -> str | None: ...

    @property
    @abstractmethod
    def max_inclusive(self) -> str | None: ...

    @property
    @abstractmethod
    def min_exclusive(self) -> str | None: ...

    @property
    @abstractmethod
    def max_exclusive(self) -> str | None: ...

    @property
    @abstractmethod
    def values_in(self) -> Iterable[str] | None: ...


class RecordConstraintAdapter(ABC):
    """The read-side interface to a record constraint."""

    @property
    @abstractmethod
    def record(self) -> str:
        """The short-code (or id) of the record referenced by this constraint."""

    @property
    @abstractmethod
    def values_in(self) -> Iterable[str] | None:
        """The IRIs of the resources allowed as values under this constraint, if any."""


class PropertyMappingAdapter(ABC):
    """The read-side interface to a property mapping (dictionary-valued property)."""

    @property
    @abstractmethod
    def key_property(self) -> str:
        """The short-code of the target object property to use as the map key."""