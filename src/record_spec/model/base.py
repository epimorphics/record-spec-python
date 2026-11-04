"""Base classes for model elements."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

    from record_spec.extensions import ExtensionRecord

    from .property import LiteralProperty, RecordProperty
    from .property_mapping import PropertyMapping
    from .values import LangString


class Documentable:
    """Base class for all model elements that support documentation."""

    def __init__(self) -> None:
        #: Display labels for the item.
        self.label: list[LangString] = []
        #: Short description of the item.
        self.summary: list[LangString] = []
        #: Verbose description of the item.
        self.description: list[LangString] = []


class Extensible(ABC):
    """Interface for model elements that can be annotated with extension records."""

    @property
    @abstractmethod
    def extensions(self) -> Iterable[ExtensionRecord]: ...

    @abstractmethod
    def add_extension_record(self, extension_record: ExtensionRecord) -> None: ...

    @abstractmethod
    def remove_extension_record(self, extension_record: ExtensionRecord) -> None: ...


class PropertyFactory(ABC):
    """Interface for objects that support the creation of property definitions."""

    @abstractmethod
    def create_record_property(
        self,
        short_code: str,
        uri: str,
        required: bool = False,
        repeatable: bool = False,
        nested: bool = False,
        reversed: bool = False,
        property_mapping: PropertyMapping | None = None,
    ) -> RecordProperty: ...

    @abstractmethod
    def create_literal_property(
        self,
        short_code: str,
        uri: str,
        required: bool = False,
        repeatable: bool = False,
    ) -> LiteralProperty: ...