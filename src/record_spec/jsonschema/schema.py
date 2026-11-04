"""Typed JSON-Schema (draft-07) builders (the Kotlin ``JsonSchema`` classes).

The classes here model the subset of JSON Schema that
:class:`~record_spec.jsonschema.builder.JsonSchemaBuilder` emits; each
serializes via :meth:`JsonSchema.to_dict`, omitting empty values
(mirroring Jackson's ``JsonInclude.NON_EMPTY``).
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping


class JsonSchemaType(Enum):
    """The JSON Schema ``type`` values used by the builder (plus ``x-langString``)."""

    NULL = "null"
    ARRAY = "array"
    OBJECT = "object"
    BOOLEAN = "boolean"
    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    LANGSTRING = "x-langString"


class JsonSchema:
    """A JSON Schema (draft-07) node."""

    def __init__(
        self,
        id: str | None = None,
        schema: str | None = None,
        type: JsonSchemaType | None = None,
        items: JsonSchema | None = None,
        properties: Mapping[str, JsonSchema] | None = None,
        required: list[str] | None = None,
        defs: Mapping[str, JsonSchema] | None = None,
        pattern: str | None = None,
        minimum: int | float | None = None,
        exclusive_minimum: int | float | None = None,
        maximum: int | float | None = None,
        exclusive_maximum: int | float | None = None,
        all_of: list[JsonSchema] | None = None,
        any_of: list[JsonSchema] | None = None,
        min_items: int | None = None,
        enum: list[Any] | None = None,
        ref: str | None = None,
        additional_properties: bool | JsonSchema | None = None,
    ):
        self.id = id
        self.schema = schema
        self.type = type
        self.items = items
        self.properties = dict(properties) if properties is not None else None
        self.required = required
        self.defs = dict(defs) if defs is not None else None
        self.pattern = pattern
        self.minimum = minimum
        self.exclusive_minimum = exclusive_minimum
        self.maximum = maximum
        self.exclusive_maximum = exclusive_maximum
        self.all_of = all_of
        self.any_of = any_of
        self.min_items = min_items
        self.enum = enum
        self.ref = ref
        self.additional_properties = additional_properties

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dict, omitting null and empty values (NON_EMPTY)."""
        result: dict[str, Any] = {}
        if self.id is not None:
            result["$id"] = self.id
        if self.schema is not None:
            result["$schema"] = self.schema
        if self.type is not None:
            result["type"] = self.type.value
        if self.items is not None:
            result["items"] = self.items.to_dict()
        if self.properties:
            result["properties"] = {key: value.to_dict() for key, value in self.properties.items()}
        if self.required:
            result["required"] = list(self.required)
        if self.defs:
            result["definitions"] = {key: value.to_dict() for key, value in self.defs.items()}
        if self.pattern is not None and self.pattern != "":
            result["pattern"] = self.pattern
        if self.minimum is not None:
            result["minimum"] = self.minimum
        if self.exclusive_minimum is not None:
            result["exclusiveMinimum"] = self.exclusive_minimum
        if self.maximum is not None:
            result["maximum"] = self.maximum
        if self.exclusive_maximum is not None:
            result["exclusiveMaximum"] = self.exclusive_maximum
        if self.all_of:
            result["allOf"] = [schema.to_dict() for schema in self.all_of]
        if self.any_of:
            result["anyOf"] = [schema.to_dict() for schema in self.any_of]
        if self.min_items is not None:
            result["minItems"] = self.min_items
        if self.enum:
            result["enum"] = list(self.enum)
        if self.ref is not None:
            result["$ref"] = self.ref
        if self.additional_properties is not None:
            if isinstance(self.additional_properties, JsonSchema):
                result["additionalProperties"] = self.additional_properties.to_dict()
            else:
                result["additionalProperties"] = self.additional_properties
        return result


class Root(JsonSchema):
    """The root schema of a generated JSON schema document."""


class Ref(JsonSchema):
    """A ``$ref`` schema."""

    def __init__(self, ref: str):
        super().__init__(ref=ref)


class ArraySchema(JsonSchema):
    def __init__(self, items: JsonSchema, min_items: int | None = None):
        super().__init__(type=JsonSchemaType.ARRAY, items=items, min_items=min_items)


class StringSchema(JsonSchema):
    def __init__(self, pattern: str | None = None, enum: list[str] | None = None):
        super().__init__(type=JsonSchemaType.STRING, pattern=pattern, enum=enum)


class IntegerSchema(JsonSchema):
    def __init__(
        self,
        min_inclusive: int | None = None,
        max_inclusive: int | None = None,
        min_exclusive: int | None = None,
        max_exclusive: int | None = None,
    ):
        super().__init__(
            type=JsonSchemaType.INTEGER,
            minimum=min_inclusive,
            maximum=max_inclusive,
            exclusive_minimum=min_exclusive,
            exclusive_maximum=max_exclusive,
        )


class NumberSchema(JsonSchema):
    def __init__(
        self,
        min_inclusive: float | None = None,
        max_inclusive: float | None = None,
        min_exclusive: float | None = None,
        max_exclusive: float | None = None,
    ):
        super().__init__(
            type=JsonSchemaType.NUMBER,
            minimum=min_inclusive,
            maximum=max_inclusive,
            exclusive_minimum=min_exclusive,
            exclusive_maximum=max_exclusive,
        )


class ObjectSchema(JsonSchema):
    def __init__(
        self,
        properties: Mapping[str, JsonSchema] | None = None,
        required: list[str] | None = None,
        additional_properties: bool | None = None,
    ):
        super().__init__(
            type=JsonSchemaType.OBJECT,
            properties=properties,
            required=required if required else None,
            additional_properties=additional_properties,
        )


class BooleanSchema(JsonSchema):
    def __init__(self) -> None:
        super().__init__(type=JsonSchemaType.BOOLEAN)


class AllOf(JsonSchema):
    def __init__(self, schemas: Iterable[JsonSchema]):
        super().__init__(all_of=list(schemas))


class AnyOf(JsonSchema):
    def __init__(self, schemas: Iterable[JsonSchema]):
        super().__init__(any_of=list(schemas))


class MappingSchema(JsonSchema):
    """An object schema whose additional properties conform to a schema."""

    def __init__(self, additional_properties: JsonSchema):
        super().__init__(type=JsonSchemaType.OBJECT, additional_properties=additional_properties)