"""The extension mechanism: extension records, services and service providers.

Extension services are discovered via `importlib.metadata` entry points in the
``record_spec.extension_service_provider`` group (the Python equivalent of the
Kotlin implementation's Java ``ServiceLoader`` SPI).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from importlib import resources
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from record_spec.model import Extensible, Schema

#: The entry-point group used to discover extension service providers.
ENTRY_POINT_GROUP = "record_spec.extension_service_provider"


class ExtensionRecord(ABC):
    """Interface for an extension record annotating a model element."""

    @property
    @abstractmethod
    def type(self) -> str:
        """The RDF type associated with this record."""

    @abstractmethod
    def to_tree(self) -> dict[str, Any]:
        """Return the tree (JSON object) that represents the data for this record."""

    @abstractmethod
    def clone(self) -> ExtensionRecord:
        """Create a separate deep clone of this record."""

    @abstractmethod
    def validate(self, parent: Extensible) -> None:
        """Validate this extension record.

        :param parent: the model item this record annotates.
        :raises record_spec.exceptions.InvalidExtensionException: on validation failure.
        """


def to_tree_with_type(extension_record: ExtensionRecord) -> dict[str, Any]:
    """Return the extension record's tree with its type included."""
    tree = dict(extension_record.to_tree())
    tree.setdefault("type", extension_record.type)
    return tree


class ExtensionService(ABC):
    """Interface for a service that processes extension records of a given type."""

    @abstractmethod
    def tree_to_record(self, tree: dict[str, Any]) -> ExtensionRecord:
        """Process a JSON object which contains the data for an extension record
        to produce an instance that implements :class:`ExtensionRecord`."""

    @property
    @abstractmethod
    def schema(self) -> Schema:
        """The schema for the extension records that this service accepts."""


class ExtensionServiceProvider(ABC):
    """Interface for a provider of one or more extension services."""

    @abstractmethod
    def handles_type(self, extension_type: str) -> bool:
        """Return True if this provider can handle extensions of the specified type."""

    @abstractmethod
    def get_extension_service(self, extension_type: str) -> ExtensionService | None:
        """Return the :class:`ExtensionService` that handles ``extension_type``,
        or None if this provider does not support it."""

    @abstractmethod
    def list_services(self) -> Iterable[ExtensionService]:
        """Return all the :class:`ExtensionService` instances provided."""


class UnrecognizedExtensionRecord(ExtensionRecord):
    """An extension record whose type is not handled by any loaded extension service."""

    def __init__(self, extension_type: str, tree: dict[str, Any]):
        self._type = extension_type
        self._tree = tree

    @property
    def type(self) -> str:
        return self._type

    def to_tree(self) -> dict[str, Any]:
        return dict(self._tree)

    def clone(self) -> UnrecognizedExtensionRecord:
        return UnrecognizedExtensionRecord(self._type, dict(self._tree))

    def validate(self, parent: Extensible) -> None:
        # no-op
        pass


def _service_providers() -> list[ExtensionServiceProvider]:
    """Load all registered extension service providers via entry points."""
    from importlib.metadata import entry_points

    providers = []
    for entry_point in entry_points(group=ENTRY_POINT_GROUP):
        provider = entry_point.load()
        providers.append(provider() if isinstance(provider, type) else provider)
    return providers


def get_extension_service(extension_type: str) -> ExtensionService | None:
    """Return the extension service that handles extensions of the specified type,
    or None if no such service is available."""
    for provider in _service_providers():
        if provider.handles_type(extension_type):
            service = provider.get_extension_service(extension_type)
            if service is not None:
                return service
    return None


def get_combined_schema() -> Schema:
    """Create a :class:`Schema` representing the core record-spec schema merged
    with the schemas provided by each of the loaded extension service providers."""
    from record_spec.model import SchemaBuilder
    from record_spec.yaml_parser import YamlParser

    bundled = resources.files("record_spec").joinpath("resources/schema.yaml").read_text()
    schema = SchemaBuilder().build(YamlParser().parse(bundled), None, validate=False)
    merged_schema_identifiers: set[str] = set()
    for provider in _service_providers():
        for service in provider.list_services():
            service_schema = service.schema
            service_schema_identifier = service_schema.identifier
            if service_schema_identifier is None:
                schema.merge(service_schema)
            elif service_schema_identifier not in merged_schema_identifiers:
                merged_schema_identifiers.add(service_schema_identifier)
                schema.merge(service_schema)
    return schema