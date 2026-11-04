"""A simple extension service for testing, plus its provider.

The Python equivalent of the Kotlin ``SimpleTestService`` /
``TestExtensionServiceProvider`` test fixtures.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from record_spec.exceptions import InvalidExtensionException
from record_spec.extensions import (
    ExtensionRecord,
    ExtensionService,
    ExtensionServiceProvider,
    register_provider,
    unregister_provider,
)
from record_spec.model import Extensible, SchemaBuilder
from record_spec.yaml_parser import YamlParser

if TYPE_CHECKING:

    from collections.abc import Iterable

    from record_spec.model import Schema

SIMPLE_EXTENSION_TYPE = "http://epimorphics.com/record-spec/extension/simple"


class SimpleExtensionRecord(ExtensionRecord):
    """A simple extension record with a single ``value`` property."""

    def __init__(self, value: str | None = None, type: str = SIMPLE_EXTENSION_TYPE):
        self.value = value
        self._type = type

    @property
    def type(self) -> str:
        return self._type

    def to_tree(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        if self.value is not None:
            result["value"] = self.value
        return result

    def clone(self) -> SimpleExtensionRecord:
        return SimpleExtensionRecord(self.value, self._type)

    def validate(self, parent: Extensible) -> None:
        if self.value == "fail":
            raise InvalidExtensionException("Extension value is 'fail'")

    def __repr__(self) -> str:
        return f"SimpleExtensionRecord(value={self.value!r})"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, SimpleExtensionRecord) and self.value == other.value and self._type == other._type


class SimpleTestService(ExtensionService):
    """The service handling the simple extension type."""

    RECORD_TYPE = SIMPLE_EXTENSION_TYPE

    def tree_to_record(self, tree: dict[str, Any]) -> SimpleExtensionRecord:
        value = tree.get("value")
        return SimpleExtensionRecord(value if isinstance(value, str) else None)

    @property
    def schema(self) -> Schema:
        import pathlib

        schema_path = pathlib.Path(__file__).parent / "resources" / "extensions" / "extension_service.yaml"
        with open(schema_path) as source:
            return SchemaBuilder().build(YamlParser().parse(source), None, validate=False)


class TestExtensionServiceProvider(ExtensionServiceProvider):
    """A provider backed by an explicit registry of services (the Kotlin
    ``TestExtensionServiceProvider``)."""

    def __init__(self) -> None:
        self._registered: dict[str, ExtensionService] = {}

    def handles_type(self, extension_type: str) -> bool:
        return extension_type in self._registered

    def get_extension_service(self, extension_type: str) -> ExtensionService | None:
        return self._registered.get(extension_type)

    def list_services(self) -> Iterable[ExtensionService]:
        return list(self._registered.values())

    def register_service(self, extension_type: str, service: ExtensionService) -> None:
        self._registered[extension_type] = service

    def unregister_service(self, extension_type: str) -> None:
        self._registered.pop(extension_type, None)

    def clear_registered_services(self) -> None:
        self._registered.clear()


#: The shared provider instance used by the extension tests (registered
#: globally so SchemaBuilder's extension deserialization sees it, mirroring
#: the Kotlin tests' ServiceLoader registration).
PROVIDER = TestExtensionProvider = TestExtensionServiceProvider()


def register_simple_service() -> None:
    """Register the simple test service with the shared test provider."""
    PROVIDER.register_service(SIMPLE_EXTENSION_TYPE, SimpleTestService())
    try:
        register_provider(PROVIDER)
    except ValueError:
        pass  # already registered


def unregister_simple_service() -> None:
    """Unregister the simple test service and (if empty) the provider."""
    PROVIDER.unregister_service(SIMPLE_EXTENSION_TYPE)
    unregister_provider(PROVIDER)


def clear_registered_services() -> None:
    PROVIDER.clear_registered_services()
    unregister_provider(PROVIDER)