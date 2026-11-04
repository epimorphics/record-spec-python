"""JSON Schema and JSON-LD context generation."""

from record_spec.jsonschema.builder import JsonSchemaBuilder, build_schema_json
from record_spec.jsonschema.context_builder import JsonLdContextBuilder
from record_spec.jsonschema.options import JsonOptions
from record_spec.jsonschema.schema import (
    AllOf,
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

__all__ = [
    "JsonOptions",
    "JsonSchemaBuilder",
    "build_schema_json",
    "JsonLdContextBuilder",
    "JsonSchema",
    "JsonSchemaType",
    "Root",
    "Ref",
    "ArraySchema",
    "StringSchema",
    "IntegerSchema",
    "NumberSchema",
    "ObjectSchema",
    "BooleanSchema",
    "AllOf",
    "AnyOf",
    "MappingSchema",
]