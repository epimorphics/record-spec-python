"""Builds a JSON Schema (draft-07) document from a record-spec schema.

The rdflib-independent equivalent of the Kotlin ``JsonSchemaBuilder``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from record_spec.model.constraints import LiteralConstraint
from record_spec.model.property import LiteralProperty, Property, RecordProperty
from record_spec.values.datatypes import RDF_LANG_STRING, XSD

from .options import JsonOptions
from .schema import (
    AnyOf,
    ArraySchema,
    BooleanSchema,
    IntegerSchema,
    JsonSchema,
    JsonSchemaType,
    MappingSchema,
    NumberSchema,
    ObjectSchema,
    Ref,
    Root,
    StringSchema,
)

if TYPE_CHECKING:

    from record_spec.convert import SchemaAdapter
    from record_spec.model import Record, RecordConstraint, Schema


def _to_long(value: str) -> int | None:
    """Mirror Kotlin's ``String.toLongOrNull``."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _to_double(value: str) -> float | None:
    """Mirror Kotlin's ``String.toDoubleOrNull``."""
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


class JsonSchemaBuilder:
    """Builds JSON Schema documents from record-spec schemas or records."""

    def __init__(self, options: JsonOptions | None = None):
        self.options = options if options is not None else JsonOptions()
        self._record_refs: list[Record] = []

    def build(self, source: Schema | Record, schema_id: str | None = None) -> dict[str, Any]:
        """Build a JSON Schema document for a complete schema or a single record.

        For a :class:`Record`, the schema is rooted at that record (including
        its subclasses if :attr:`JsonOptions.with_subclasses` is set).
        For a :class:`Schema`, the schema covers all records in the schema.
        """
        from record_spec.model import Record

        if isinstance(source, Record):
            if schema_id is not None:  # pragma: no cover - defensive
                raise ValueError("schema_id cannot be combined with a Record source")
            root_types = list(source.all_descendents_and_self()) if self.options.with_subclasses else [source]
            return self.build_root_types(root_types, source.id)
        assert schema_id is not None
        return self.build_root_types(list(source.records), schema_id)

    def build_root_types(self, root_types: list[Record], schema_id: str) -> dict[str, Any]:
        for root_type in root_types:
            if root_type not in self._record_refs:
                self._record_refs.append(root_type)
        defs, root_ref = self._build_definitions(root_types)
        if self.options.require_array:
            record_schema: JsonSchema = Root(
                id=schema_id,
                schema="http://json-schema.org/draft-07/schema#",
                type=JsonSchemaType.ARRAY,
                items=Ref(root_ref),
                defs=defs,
            )
        elif self.options.allow_array:
            record_schema = Root(
                id=schema_id,
                schema="http://json-schema.org/draft-07/schema#",
                any_of=[Ref(root_ref), ArraySchema(Ref(root_ref))],
                defs=defs,
            )
        else:
            record_schema = Root(
                id=schema_id,
                schema="http://json-schema.org/draft-07/schema#",
                ref=root_ref,
                defs=defs,
            )
        return record_schema.to_dict()

    def get_properties(self, record: Record, with_id: bool, skip_property: str | None) -> dict[str, JsonSchema]:
        map_: dict[str, JsonSchema] = {}
        if with_id:
            map_[self.options.id_property] = StringSchema()
        map_[self.options.type_property] = StringSchema(enum=[record.class_uri])
        if self.options.allow_json_ld_context:
            map_["@context"] = AnyOf([StringSchema(), ObjectSchema(additional_properties=True)])
        if self.options.allow_json_schema_ref:
            map_["$schema"] = StringSchema()
        for prop in record.effective_properties:
            if prop.short_code == skip_property:
                continue
            map_[prop.short_code] = self.build_property(prop)
        return map_

    def build_record_schema(self, record: Record, skip_property: str | None = None) -> JsonSchema:
        return ObjectSchema(
            properties=self.get_properties(record, True, skip_property),
            required=self._get_required_properties(record, skip_property),
            additional_properties=None if self.options.additional_properties else False,
        )

    def _get_required_properties(self, record: Record, skip_property: str | None) -> list[str]:
        required_properties = [
            prop.short_code
            for prop in record.effective_properties
            if prop.required and prop.short_code != skip_property
        ]
        if self.options.optional_type_property:
            return required_properties
        # The required type property follows options.type_property (#66 upstream).
        return list(dict.fromkeys(required_properties + [self.options.type_property]))

    def build_property(self, prop: Property) -> JsonSchema:
        if isinstance(prop, LiteralProperty):
            return self._build_literal_property(prop)
        if isinstance(prop, RecordProperty):
            return self._build_record_property(prop)
        raise ValueError(f"Unsupported property type: {type(prop)!r}")

    def _build_literal_property(self, prop: LiteralProperty) -> JsonSchema:
        json_literal_types = [self._json_literal_type(c.datatype) for c in prop.constraints]
        typed_literal = any(t == JsonSchemaType.OBJECT for t in json_literal_types)
        structured_literal = typed_literal or any(t == JsonSchemaType.LANGSTRING for t in json_literal_types)
        json_literal_schemas = [self._build_literal_constraint(c, structured_literal) for c in prop.constraints]
        if len(json_literal_schemas) == 0:
            schema: JsonSchema = self._make_open_literal_schema()
        elif len(json_literal_schemas) == 1:
            if typed_literal:
                first = json_literal_schemas[0]
                value_schema = first.properties.get(self.options.value_property) if first.properties else None
                pattern = value_schema.pattern if value_schema is not None else None
                schema = AnyOf([first, StringSchema(pattern=pattern)])
            else:
                schema = json_literal_schemas[0]
        else:
            schema = AnyOf(json_literal_schemas)
        return self._wrap_if_repeatable(prop, schema)

    def _build_literal_constraint(self, constraint: LiteralConstraint, as_structured_literal: bool) -> JsonSchema:
        json_literal_type = self._json_literal_type(constraint.datatype)
        if as_structured_literal:
            if json_literal_type == JsonSchemaType.LANGSTRING:
                return self._make_lang_string_literal_schema(constraint.pattern)
            return self._make_datatyped_literal_schema(constraint.datatype, constraint.pattern)
        if json_literal_type == JsonSchemaType.STRING:
            return StringSchema(constraint.pattern)
        if json_literal_type == JsonSchemaType.INTEGER:
            return IntegerSchema(
                _to_long(constraint.min_inclusive) if constraint.min_inclusive is not None else None,
                _to_long(constraint.max_inclusive) if constraint.max_inclusive is not None else None,
                _to_long(constraint.min_exclusive) if constraint.min_exclusive is not None else None,
                _to_long(constraint.max_exclusive) if constraint.max_exclusive is not None else None,
            )
        if json_literal_type == JsonSchemaType.NUMBER:
            return NumberSchema(
                _to_double(constraint.min_inclusive) if constraint.min_inclusive is not None else None,
                _to_double(constraint.max_inclusive) if constraint.max_inclusive is not None else None,
                _to_double(constraint.min_exclusive) if constraint.min_exclusive is not None else None,
                _to_double(constraint.max_exclusive) if constraint.max_exclusive is not None else None,
            )
        if json_literal_type == JsonSchemaType.BOOLEAN:
            return BooleanSchema()
        if json_literal_type == JsonSchemaType.OBJECT:
            return self._make_datatyped_literal_schema(constraint.datatype, constraint.pattern)
        if json_literal_type == JsonSchemaType.LANGSTRING:
            return self._make_lang_string_literal_schema(constraint.pattern)
        raise Exception(f"Unexpected JSON literal range for literal property: {json_literal_type}")

    def _make_open_literal_schema(self) -> JsonSchema:
        return ObjectSchema(
            properties={
                self.options.value_property: StringSchema(),
                self.options.type_property: StringSchema(),
            },
            required=[self.options.value_property, self.options.type_property],
        )

    def _make_datatyped_literal_schema(self, datatype: str, pattern: str | None) -> JsonSchema:
        return ObjectSchema(
            properties={
                self.options.value_property: StringSchema(pattern=pattern),
                self.options.type_property: StringSchema(enum=[datatype]),
            },
            required=(
                [self.options.value_property]
                if datatype == XSD + "string"
                else [self.options.value_property, self.options.type_property]
            ),
        )

    def _make_lang_string_literal_schema(self, pattern: str | None) -> JsonSchema:
        return ObjectSchema(
            properties={
                self.options.value_property: StringSchema(pattern=pattern),
                self.options.language_property: StringSchema(),
                self.options.type_property: StringSchema(enum=[RDF_LANG_STRING]),
            },
            required=[self.options.value_property, self.options.language_property],
        )

    def _build_record_property(self, prop: RecordProperty) -> JsonSchema:
        if prop.property_mapping is not None:
            key_property = prop.property_mapping.key_property
            schema_list: list[JsonSchema] = []
            for constraint in prop.constraints:
                schema_list.extend(self._build_record_constraint(constraint, key_property))
            inner = schema_list[0] if len(schema_list) == 1 else AnyOf(schema_list)
            # NOTE: mapped properties are not wrapped as arrays, mirroring
            # the Kotlin original.
            return MappingSchema(inner)
        if prop.nested:
            record_schemas: list[JsonSchema] = []
            for constraint in prop.constraints:
                record_schemas.extend(self._build_record_constraint(constraint, None))
            schema = record_schemas[0] if len(record_schemas) == 1 else AnyOf(record_schemas)
        else:
            schema = Ref("#/definitions/_ref")
        return self._wrap_if_repeatable(prop, schema)

    def _wrap_if_repeatable(self, prop: Property, schema: JsonSchema) -> JsonSchema:
        if prop.repeatable:
            return ArraySchema(schema, min_items=1 if prop.required else None)
        return schema

    def _build_record_constraint(
        self, record_constraint: RecordConstraint, skip_property: str | None
    ) -> list[JsonSchema]:
        if skip_property is None:
            list_of_refs: list[JsonSchema] = []
            for subclass in record_constraint.record.all_descendents_and_self():
                if subclass not in self._record_refs:
                    self._record_refs.append(subclass)
                list_of_refs.append(Ref(f"#/definitions/{subclass.compact_id}"))
            return list_of_refs
        return [
            self.build_record_schema(descendent, skip_property)
            for descendent in record_constraint.record.all_descendents_and_self()
        ]

    def _build_definitions(self, root_types: list[Record]) -> tuple[dict[str, JsonSchema], str]:
        defs: dict[str, JsonSchema] = {}
        nested_refs: list[Record] = []
        for ref in self._record_refs:
            for nested in ref.gather_nested_records():
                if nested not in nested_refs:
                    nested_refs.append(nested)
        nested_refs_and_subclasses: list[Record] = []
        for ref in nested_refs:
            for descendent in ref.all_descendents_and_self():
                if descendent not in nested_refs_and_subclasses:
                    nested_refs_and_subclasses.append(descendent)
        if self.options.bare_reference_ids:
            defs["_ref"] = StringSchema()
        else:
            defs["_ref"] = ObjectSchema(
                properties={self.options.id_property: StringSchema()},
                required=[self.options.id_property],
                additional_properties=None if self.options.additional_properties else False,
            )
        for record in nested_refs_and_subclasses:
            defs[record.compact_id] = self.build_record_schema(record, None)
        if len(root_types) == 1:
            return defs, f"#/definitions/{root_types[0].compact_id}"
        defs["_root"] = AnyOf([Ref(f"#/definitions/{root_type.compact_id}") for root_type in root_types])
        return defs, "#/definitions/_root"

    def _json_literal_type(self, datatype: str) -> JsonSchemaType:
        if datatype == XSD + "string":
            return JsonSchemaType.STRING
        if datatype in (XSD + "integer", XSD + "long", XSD + "int"):
            return JsonSchemaType.INTEGER
        if datatype in (XSD + "float", XSD + "double"):
            return JsonSchemaType.NUMBER
        if datatype == XSD + "boolean":
            return JsonSchemaType.BOOLEAN
        if datatype == RDF_LANG_STRING:
            return JsonSchemaType.LANGSTRING
        return JsonSchemaType.OBJECT


# Convenience: keep the old name for building from a Schema/Record pair.
def build_schema_json(
    schema_adapter: SchemaAdapter | Schema | Record,
    source_uri: str | None = None,
    options: JsonOptions | None = None,
    schema_id: str | None = None,
) -> dict[str, Any]:
    """Build a JSON schema from any schema source."""
    from record_spec.model import Record, SchemaBuilder

    builder = JsonSchemaBuilder(options)
    if isinstance(schema_adapter, (Schema, Record)):
        return builder.build(schema_adapter, schema_id)
    schema = SchemaBuilder().build(schema_adapter, source_uri, True)
    return builder.build(schema, schema_id or "http://example.org/spec/schema")