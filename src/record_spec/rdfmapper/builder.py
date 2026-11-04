"""Builds rdf-mapper templates from a record-spec schema (the Kotlin ``RdfMapperBuilder``).

See the Kotlin repo's ``docs/rdf-mapper-output.md`` for the output format.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from record_spec.model.property import LiteralProperty, Property, RecordProperty
from record_spec.values.datatypes import RDF_LANG_STRING, XSD

from .model import (
    IdMapping,
    LiteralPropertyValue,
    MapTo,
    PropertyValue,
    RdfMapperModel,
    ResourceTemplate,
    SimpleMapTo,
)
from .options import RdfMapperOptions

if TYPE_CHECKING:
    from record_spec.model import Record, Schema

#: The transformer applied to plain-literal properties to filter out
#: structured (dict) values.
FILTER_DICT_TRANSFORMER = "expr('x if type(x) != dict else None')"

_XSD_STRING = XSD + "string"


class RdfMapperBuilder:
    """Builds an :class:`RdfMapperModel` for a record within a schema."""

    def __init__(self, options: RdfMapperOptions | None = None):
        self.options = options if options is not None else RdfMapperOptions()
        self._building: list[str] = []
        self.embedded_templates: dict[str, ResourceTemplate] = {}

    def build(self, schema: Schema, record: Record) -> RdfMapperModel:
        record_template = self._build_template(record, record.short_code)
        return RdfMapperModel(
            imports=["record-mapper-core.yaml"],
            namespaces={pm.prefix: pm.uri for pm in schema.prefix_mappings},
            embedded=list(self.embedded_templates.values()),
            resources=[record_template],
        )

    def _build_template(self, record: Record, template_name: str) -> ResourceTemplate:
        properties = self._build_record_properties(record)
        return ResourceTemplate(
            name=template_name,
            properties=properties,
            graph=None if self.options.graph_add else self.options.graph_pattern,
            graph_add=self.options.graph_pattern if self.options.graph_add else None,
        )

    def _get_effective_properties(self, record: Record) -> list[Property]:
        """Union of the effective properties of the record and all its descendents."""
        emitted: list[Property] = []
        for r in record.all_descendents_and_self():
            for e in r.effective_properties:
                if not any(existing.short_code == e.short_code for existing in emitted):
                    emitted.append(e)
        return emitted

    def _build_record_properties(self, record: Record) -> dict[str, list[PropertyValue]]:
        effective_properties = self._get_effective_properties(record)
        properties: dict[str, list[PropertyValue]] = {
            "@id": [IdMapping("@id")],
            "@type": [IdMapping("@type")],
        }
        for prop in effective_properties:
            if isinstance(prop, RecordProperty) and prop.reversed:
                properties[f"<^{prop.property_uri}>"] = self._build_property_mapping(prop)
            else:
                properties[f"<{prop.property_uri}>"] = self._build_property_mapping(prop)
        return properties

    def _build_nested(self, record: Record) -> ResourceTemplate:
        properties = self._build_record_properties(record)
        return ResourceTemplate(
            name=f"Nested.{record.short_code}",
            properties=properties,
            requires={"@type": [record.class_uri]},
        )

    def _build_property_mapping(self, prop: Property) -> list[PropertyValue]:
        if isinstance(prop, LiteralProperty):
            return self._build_literal_resource(prop)
        if isinstance(prop, RecordProperty):
            if prop.nested:
                return self._build_nested_resource(prop)
            return self._build_reference_resource(prop)
        raise ValueError(f"Unsupported property type: {type(prop)!r}")

    def _build_literal_resource(self, prop: LiteralProperty) -> list[PropertyValue]:
        datatypes = list(dict.fromkeys(constraint.datatype for constraint in prop.constraints))
        if len(datatypes) > 1:
            values: list[PropertyValue] = []
            if RDF_LANG_STRING in datatypes:
                values.append(SimpleMapTo(prop.short_code, "rdfLangString"))
            if any(datatype != RDF_LANG_STRING for datatype in datatypes):
                values.append(SimpleMapTo(prop.short_code, "typedLiteral"))
            if _XSD_STRING in datatypes:
                values.append(SimpleMapTo(prop.short_code, "plainLiteral"))
            return values
        if RDF_LANG_STRING in datatypes:
            # Always present as an object with @value and @language properties
            return [SimpleMapTo(prop.short_code, "rdfLangString")]
        if _XSD_STRING in datatypes:
            # Plain literal - might be present as a string or as an object with @value
            return [
                SimpleMapTo(prop.short_code, "plainLiteral"),
                LiteralPropertyValue(prop.short_code, transformers=[FILTER_DICT_TRANSFORMER]),
            ]
        if XSD + "integer" in datatypes:
            return [
                SimpleMapTo(prop.short_code, "typedLiteral"),
                LiteralPropertyValue(prop.short_code, transformers=["asInt"]),
            ]
        if XSD + "decimal" in datatypes:
            return [
                SimpleMapTo(prop.short_code, "typedLiteral"),
                LiteralPropertyValue(prop.short_code, transformers=["asDecimal"]),
            ]
        if XSD + "boolean" in datatypes:
            return [
                SimpleMapTo(prop.short_code, "typedLiteral"),
                LiteralPropertyValue(prop.short_code, transformers=["asBoolean"]),
            ]
        if XSD + "date" in datatypes:
            return [
                SimpleMapTo(prop.short_code, "typedLiteral"),
                LiteralPropertyValue(prop.short_code, transformers=["asDate"]),
            ]
        if XSD + "dateTime" in datatypes:
            return [
                SimpleMapTo(prop.short_code, "typedLiteral"),
                LiteralPropertyValue(prop.short_code, transformers=["asDateTime"]),
            ]
        return [SimpleMapTo(prop.short_code, "typedLiteral")]

    def _build_nested_resource(self, prop: RecordProperty) -> list[PropertyValue]:
        values: list[PropertyValue] = []
        for constraint in prop.constraints:
            for nested_record in constraint.record.all_descendents_and_self():
                embedded_template_name = self._get_or_build_embedded_template(nested_record)
                values.append(MapTo(prop.short_code, embedded_template_name))
        return values

    def _get_or_build_embedded_template(self, record: Record) -> str:
        embedded_template_name = f"Nested.{record.short_code}"
        if embedded_template_name not in self.embedded_templates:
            if embedded_template_name in self._building:
                return embedded_template_name
            self._building.append(embedded_template_name)
            self.embedded_templates[embedded_template_name] = self._build_nested(record)
            self._building.pop()
        return embedded_template_name

    def _build_reference_resource(self, prop: RecordProperty) -> list[PropertyValue]:
        # Reference properties will always be an object (or an array of
        # objects) with an @id property
        return [MapTo(prop.short_code, "ref")]