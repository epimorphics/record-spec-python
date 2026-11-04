"""The rdf-mapper template model (the Kotlin ``RdfMapperModel``).

Each template property value serializes as a string in the rdf-mapper
template syntax, e.g. ``"{label | smap_to('rdfLangString')}"``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Mapping


def _unwrap_single(values: list[Any] | None) -> Any:
    """Implement Jackson's WRITE_SINGLE_ELEM_ARRAYS_UNWRAPPED: a list with a
    single element serializes as the element itself."""
    if values is None:
        return None
    if len(values) == 1:
        return values[0].to_dict() if isinstance(values[0], PropertyValue) else values[0]
    return [value.to_dict() if isinstance(value, PropertyValue) else value for value in values]


class PropertyValue:
    """Base class for the values in a resource template's property mapping."""

    def to_dict(self) -> Any:
        """Serialize this value to its rdf-mapper template string (or tree)."""
        raise NotImplementedError


class IdMapping(PropertyValue):
    """Maps a property to the resource IRI, e.g. ``"<{@id}>"``."""

    def __init__(self, id_property: str):
        self.id_property = id_property

    def to_dict(self) -> str:
        return f"<{{{self.id_property}}}>"


class MapTo(PropertyValue):
    """Maps a property to an embedded template, e.g. ``"{foo | map_to('Nested.Foo')}"``."""

    def __init__(self, property_name: str, embedded_template_name: str):
        self.property_name = property_name
        self.embedded_template_name = embedded_template_name

    def to_dict(self) -> str:
        return f"{{{self.property_name} | map_to('{self.embedded_template_name}')}}"


class SimpleMapTo(PropertyValue):
    """Maps a property to a core template, e.g. ``"{foo | smap_to('plainLiteral')}"``."""

    def __init__(self, property_name: str, embedded_template_name: str):
        self.property_name = property_name
        self.embedded_template_name = embedded_template_name

    def to_dict(self) -> str:
        return f"{{{self.property_name} | smap_to('{self.embedded_template_name}')}}"


class IriMapping(PropertyValue):
    """Maps a property to a fixed IRI, e.g. ``"<http://example.org/foo>"``."""

    def __init__(self, iri: str):
        self.iri = iri

    def to_dict(self) -> str:
        return f"<{self.iri}>"


class LiteralPropertyValue(PropertyValue):
    """Maps a property to a literal value with optional language/datatype and transformers."""

    def __init__(
        self,
        value_property: str,
        language_property: str | None = None,
        type_property: str | None = None,
        type_val: str | None = None,
        transformers: list[str] | None = None,
    ):
        self.value_property = value_property
        self.language_property = language_property
        self.type_property = type_property
        self.type_val = type_val
        self.transformers = transformers

    def to_dict(self) -> str:
        language_tag = f"@{{{self.language_property}}}" if self.language_property else ""
        if not self.type_property:
            type_tag = f"^^<{self.type_val}>" if self.type_val else ""
        else:
            type_tag = f"^^<{{{self.type_property}}}>"
        value_mapping = self.value_property + (
            " | " + " | ".join(self.transformers) if self.transformers else ""
        )
        return f"{{{value_mapping}}}{language_tag}{type_tag}"


class ResourceTemplate(PropertyValue):
    """A resource template within an rdf-mapper model."""

    def __init__(
        self,
        name: str,
        comment: str | None = None,
        requires: Mapping[str, list[str]] | None = None,
        unless: Mapping[str, list[str]] | None = None,
        graph: str | None = None,
        graph_add: str | None = None,
        properties: Mapping[str, list[PropertyValue]] | None = None,
    ):
        self.name = name
        self.comment = comment
        self.requires = dict(requires) if requires is not None else None
        self.unless = dict(unless) if unless is not None else None
        self.graph = graph
        self.graph_add = graph_add
        self.properties = dict(properties) if properties is not None else None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"name": self.name}
        if self.comment:
            result["comment"] = self.comment
        if self.requires:
            result["requires"] = {key: _unwrap_single(values) for key, values in self.requires.items()}
        if self.unless:
            result["unless"] = {key: _unwrap_single(values) for key, values in self.unless.items()}
        if self.graph is not None:
            result["@graph"] = self.graph
        if self.graph_add is not None:
            result["@graphAdd"] = self.graph_add
        if self.properties:
            result["properties"] = {key: _unwrap_single(values) for key, values in self.properties.items()}
        return result


class RdfMapperModel:
    """The complete rdf-mapper template model."""

    def __init__(
        self,
        namespaces: Mapping[str, str] | None = None,
        imports: list[str] | None = None,
        resources: list[ResourceTemplate] | None = None,
        one_offs: Mapping[str, ResourceTemplate] | None = None,
        embedded: list[ResourceTemplate] | None = None,
        mappings: Mapping[str, Mapping[str, str]] | None = None,
    ):
        self.namespaces = dict(namespaces) if namespaces is not None else None
        self.imports = list(imports) if imports is not None else None
        self.resources = list(resources) if resources is not None else None
        self.one_offs = dict(one_offs) if one_offs is not None else None
        self.embedded = list(embedded) if embedded is not None else None
        self.mappings = (
            {key: dict(value) for key, value in mappings.items()} if mappings is not None else None
        )

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        if self.namespaces:
            result["namespaces"] = dict(self.namespaces)
        if self.imports:
            result["imports"] = list(self.imports)
        if self.resources:
            result["resources"] = [resource.to_dict() for resource in self.resources]
        if self.one_offs:
            result["one_offs"] = {key: value.to_dict() for key, value in self.one_offs.items()}
        if self.embedded:
            result["embedded"] = [resource.to_dict() for resource in self.embedded]
        if self.mappings:
            result["mappings"] = {key: dict(value) for key, value in self.mappings.items()}
        return result