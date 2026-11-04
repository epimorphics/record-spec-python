"""Port of the Kotlin ``PropertyMappingTests``."""

from __future__ import annotations

import pytest

from record_spec.exceptions import (
    InvalidPropertyMapException,
    SchemaValidationException,
)
from record_spec.model import PropertyMapping, RecordProperty, Schema
from record_spec.values import XSD


def _make_schema_with_foo_and_bar():
    schema = Schema()
    foo = schema.create_record("http://example.org/record/Foo", "http://example.org/def/Foo", "Foo")
    foo.create_literal_property("notation", "http://example.org/def/notation", required=True).add_constraint(
        XSD + "string"
    )
    foo.create_literal_property(
        "labels", "http://example.org/def/label", required=False, repeatable=True
    ).add_constraint(XSD + "string")
    bar = schema.create_record("http://example.org/record/Bar", "http://example.org/def/Bar", "Bar")
    return schema, foo, bar


def _assert_invalid_property_exception_on_validation(
    schema: Schema, invalid_record, invalid_property: RecordProperty
) -> InvalidPropertyMapException:
    with pytest.raises(SchemaValidationException) as exc_info:
        schema.validate()
    sve = exc_info.value
    ire = sve.validation_errors[0]
    assert ire.record == invalid_record
    ipe = ire.cause
    assert ipe.property == invalid_property
    return ipe.cause


def test_key_only_property_map():
    schema, foo, bar = _make_schema_with_foo_and_bar()
    foo_map = bar.create_record_property(
        "fooMap", "http://example.org/def/FooMap", required=True, repeatable=True, nested=True
    )
    foo_map.add_constraint("http://example.org/record/Foo")
    foo_map.set_property_map(PropertyMapping("notation"))
    schema.validate()


def test_mapped_property_must_be_nested():
    schema, foo, bar = _make_schema_with_foo_and_bar()
    foo_map = bar.create_record_property("fooMap", "http://example.org/def/FooMap", required=True, repeatable=True)
    foo_map.add_constraint("http://example.org/record/Foo")
    foo_map.set_property_map(PropertyMapping("notation"))
    _assert_invalid_property_exception_on_validation(schema, bar, foo_map)


def test_key_property_must_exist():
    schema, foo, bar = _make_schema_with_foo_and_bar()
    foo_map = bar.create_record_property(
        "fooMap", "http://example.org/def/FooMap", required=True, repeatable=True, nested=True
    )
    foo_map.add_constraint("http://example.org/record/Foo")
    foo_map.set_property_map(PropertyMapping("nonExistentProperty"))
    ipme = _assert_invalid_property_exception_on_validation(schema, bar, foo_map)
    assert ipme.property_mapping.key_property == "nonExistentProperty"


def test_key_property_must_exist_on_all_records_in_range():
    schema, foo, bar = _make_schema_with_foo_and_bar()
    baz = schema.create_record("http://example.org/record/Baz", "http://example.org/record/baz", "Baz")
    baz.create_literal_property("identifier", "http://example.org/def/notation", True).add_constraint(XSD + "string")
    baz.create_literal_property(
        "labels", "http://example.org/def/label", required=False, repeatable=True
    ).add_constraint(XSD + "string")
    foo_map = bar.create_record_property(
        "fooMap", "http://example.org/def/FooMap", required=True, repeatable=True, nested=True
    )
    foo_map.add_constraint("http://example.org/record/Foo")
    foo_map.add_constraint("http://example.org/record/Baz")
    foo_map.set_property_map(PropertyMapping("notation"))
    ipme = _assert_invalid_property_exception_on_validation(schema, bar, foo_map)
    assert ipme.property_mapping.key_property == "notation"


def test_key_property_may_be_on_mixin():
    schema, foo, bar = _make_schema_with_foo_and_bar()
    with_notation = schema.create_mixin("http://example.org/mixin/WithNotation")
    with_notation.create_literal_property("notation", "http://example.org/def/notation", True).add_constraint(
        XSD + "string"
    )
    foo.add_mixin("http://example.org/mixin/WithNotation")
    foo_map = bar.create_record_property(
        "fooMap", "http://example.org/def/FooMap", required=True, repeatable=True, nested=True
    )
    foo_map.add_constraint("http://example.org/record/Foo")
    foo_map.set_property_map(PropertyMapping("notation"))
    schema.validate()


def test_key_property_must_be_a_literal():
    schema = Schema()
    schema.create_record("http://example.org/record/Baz", "http://example.org/def/Baz", "Baz")
    foo = schema.create_record("http://example.org/record/Foo", "http://example.org/def/Foo", "Foo")
    foo.create_record_property("notation", "http://example.org/def/notation", True).add_constraint(
        "http://example.org/record/Baz"
    )
    foo.create_literal_property(
        "labels", "http://example.org/def/label", required=False, repeatable=True
    ).add_constraint(XSD + "string")
    bar = schema.create_record("http://example.org/record/Bar", "http://example.org/def/Bar", "Bar")
    foo_map = bar.create_record_property(
        "fooMap", "http://example.org/def/FooMap", required=True, repeatable=True, nested=True
    )
    foo_map.add_constraint("http://example.org/record/Foo")
    foo_map.set_property_map(PropertyMapping("notation"))
    _assert_invalid_property_exception_on_validation(schema, bar, foo_map)


def test_key_property_must_be_required():
    schema = Schema()
    foo = schema.create_record("http://example.org/record/Foo", "http://example.org/def/Foo", "Foo")
    foo.create_literal_property(
        "notation", "http://example.org/def/notation", required=False, repeatable=False
    ).add_constraint(XSD + "string")
    bar = schema.create_record("http://example.org/record/Bar", "http://example.org/def/Bar", "Bar")
    foo_map = bar.create_record_property(
        "fooMap", "http://example.org/def/FooMap", required=True, repeatable=True, nested=True
    )
    foo_map.add_constraint("http://example.org/record/Foo")
    foo_map.set_property_map(PropertyMapping("notation"))
    _assert_invalid_property_exception_on_validation(schema, bar, foo_map)


def test_key_property_must_not_be_repeatable():
    schema = Schema()
    foo = schema.create_record("http://example.org/record/Foo", "http://example.org/def/Foo", "Foo")
    foo.create_literal_property(
        "notation", "http://example.org/def/notation", required=True, repeatable=True
    ).add_constraint(XSD + "string")
    bar = schema.create_record("http://example.org/record/Bar", "http://example.org/def/Bar", "Bar")
    foo_map = bar.create_record_property(
        "fooMap", "http://example.org/def/FooMap", required=True, repeatable=True, nested=True
    )
    foo_map.add_constraint("http://example.org/record/Foo")
    foo_map.set_property_map(PropertyMapping("notation"))
    _assert_invalid_property_exception_on_validation(schema, bar, foo_map)