"""Builds a JSON-LD context for a schema (the Kotlin ``JsonLdContextBuilder``)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from record_spec.convert import SchemaAdapter
from record_spec.model.property import LiteralProperty, RecordProperty

from .options import JsonOptions

if TYPE_CHECKING:
    from record_spec.model import Property, Record, Schema


class JsonLdContextBuilder:
    """Builds a JSON-LD context for a schema."""

    def __init__(self, options: JsonOptions | None = None):
        self.options = options if options is not None else JsonOptions()

    def make_schema_context(self, source: SchemaAdapter | Schema) -> dict[str, Any]:
        """Build a JSON-LD context for a schema.

        :param source: the adapter for the schema to be processed, or a
            built :class:`Schema`.
        :return: a dict representing the JSON-LD context object for the schema.
        """
        from record_spec.model import SchemaBuilder

        if isinstance(source, SchemaAdapter):
            schema = SchemaBuilder().build(source, None, True)
        else:
            schema = source
        context = self._make_initial_context()
        for record in schema.records:
            context[record.class_uri] = self._build_record(record)
        return context

    def make_record_context(self, record: Record) -> dict[str, Any]:
        """Build a JSON-LD context for a single record and its nested records."""
        context = self._make_initial_context()
        for nested_record in record.gather_nested_records():
            context[nested_record.class_uri] = self._build_record(nested_record)
        return context

    def _make_initial_context(self) -> dict[str, Any]:
        context: dict[str, Any] = {"@version": 1.1}
        if self.options.id_property != "@id":
            context[self.options.id_property] = "@id"
        if self.options.type_property != "@type":
            context[self.options.type_property] = "@type"
        return context

    def _build_record(self, record: Record) -> dict[str, Any]:
        term_context: dict[str, Any] = {}
        for prop in record.effective_properties:
            term_context[prop.short_code] = self._build_property(prop)
        return {"@context": term_context}

    def _build_property(self, prop: Property) -> dict[str, Any]:
        term_def: dict[str, Any] = {}
        if isinstance(prop, RecordProperty) and prop.reversed:
            term_def["@reverse"] = prop.property_uri
        else:
            term_def["@id"] = prop.property_uri
        if isinstance(prop, RecordProperty):
            if prop.nested:
                property_map = prop.property_mapping
                if property_map is not None:
                    if property_map.key_property == "@id":
                        term_def["@container"] = "@id"
                    else:
                        key_properties = [
                            record.get_property(property_map.key_property)
                            for record in prop.range
                        ]
                        key_property = next((p for p in key_properties if p is not None), None)
                        key_property_uri = key_property.property_uri if key_property is not None else None
                        term_def["@container"] = "@index"
                        term_def["@index"] = key_property_uri
                else:
                    distinct_range = [record.class_uri for record in prop.range]
                    if len(distinct_range) == 1:
                        term_def["@type"] = distinct_range[0]
            else:
                if self.options.bare_reference_ids:
                    term_def["@type"] = "@id"
        elif isinstance(prop, LiteralProperty):
            distinct_range = list(dict.fromkeys(prop.range))
            if len(distinct_range) == 1:
                term_def["@type"] = distinct_range[0]
        if prop.repeatable and "@container" not in term_def:
            # If not already mapped to an indexed collection, add @set to
            # ensure arrays are generated when framing repeatable properties.
            term_def["@container"] = "@set"
        return term_def