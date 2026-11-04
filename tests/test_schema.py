"""Port of the Kotlin ``SchemaTests``."""

from __future__ import annotations

import pytest
from helpers import load_schema

from record_spec.exceptions import (
    CircularInheritanceException,
    IncompatiblePropertyException,
    IncompatibleRangeException,
    InvalidPropertyException,
    InvalidRecordConstraintException,
    InvalidRecordException,
    InvalidReversePropertyRangeException,
    InvalidShortCodeException,
    MixinExistsException,
    MixinNotFoundException,
    MixinPropertyClashException,
    MixinReferencedException,
    PropertyClashException,
    RecordExistsException,
    RecordNotFoundException,
    RecordReferencedException,
    RecordShortCodeClashException,
    SchemaValidationException,
)
from record_spec.model import RecordProperty, Schema
from record_spec.values import XSD


def test_create_record_adds_record_to_schema():
    schema = Schema()
    schema.create_record("http://example.org/record", "http://example.org/def/Thing", "Thing")
    assert len(list(schema.records)) == 1
    assert schema.requires_validation


def test_create_record_throws_on_duplicate_id():
    schema = Schema()
    schema.create_record("http://example.org/record", "http://example.org/def/Thing", "Thing")
    with pytest.raises(RecordExistsException) as exc_info:
        schema.create_record("http://example.org/record", "http://example.org/def/Thing", "Thing")
    assert exc_info.value.attribute_name == "id"
    assert exc_info.value.attribute_value == "http://example.org/record"


def test_resolve_record_resolves_with_id():
    schema = Schema()
    schema.create_record("http://example.org/record", "http://example.org/def/Thing", "Thing")
    rec = schema.resolve_record("http://example.org/record")
    assert rec.class_uri == "http://example.org/def/Thing"


def test_resolve_record_resolves_with_relative_iri():
    schema = Schema()
    schema.set_base("http://example.org/schema")
    schema.create_record("http://example.org/record", "http://example.org/def/Thing", "Thing")
    rec = schema.resolve_record("record")
    assert rec.class_uri == "http://example.org/def/Thing"


def test_resolve_record_resolves_with_curie():
    schema = Schema()
    schema.set_prefix_mapping("ex", "http://example.org/")
    schema.create_record("http://example.org/record", "http://example.org/def/Thing", "Thing")
    rec = schema.resolve_record("ex:record")
    assert rec.class_uri == "http://example.org/def/Thing"


def test_delete_record_throws_if_record_is_referenced():
    schema = Schema()
    base = schema.create_record("http://example.org/base", "http://example.org/def/Base", "Base")
    derived = schema.create_record("http://example.org/derived", "http://example.org/def/Derived", "Derived")
    derived.set_parent(base.id)
    with pytest.raises(RecordReferencedException):
        schema.delete_record(base.id)
    assert len(list(schema.records)) == 2


def test_delete_record_succeeds_if_record_is_not_referenced():
    schema = Schema()
    base = schema.create_record("http://example.org/base", "http://example.org/def/Base", "Base")
    derived = schema.create_record("http://example.org/derived", "http://example.org/def/Derived", "Derived")
    derived.set_parent(base.id)
    schema.validate()
    assert not schema.requires_validation
    schema.delete_record(derived.id)
    assert len(list(schema.records)) == 1
    # validation not required after delete
    assert not schema.requires_validation


def test_create_mixin_adds_mixin_to_schema():
    schema = Schema()
    schema.create_mixin("http://example.org/mixinA")
    assert len(list(schema.mixins)) == 1
    assert schema.requires_validation


def test_create_mixin_throws_on_duplicate_id():
    schema = Schema()
    schema.create_mixin("http://example.org/mixinA")
    schema.validate()
    with pytest.raises(MixinExistsException):
        schema.create_mixin("http://example.org/mixinA")
    assert len(list(schema.mixins)) == 1
    assert not schema.requires_validation


def test_delete_mixin_throws_if_mixin_is_referenced():
    schema = Schema()
    mixin = schema.create_mixin("http://example.org/mixinA")
    record = schema.create_record("http://example.org/record", "http://example.org/def/Record", "Record")
    record.add_mixin(mixin.id)
    with pytest.raises(MixinReferencedException):
        schema.delete_mixin(mixin.id)


def test_delete_mixin_succeeds_if_mixin_is_not_referenced():
    schema = Schema()
    mixin = schema.create_mixin("http://example.org/mixinA")
    schema.delete_mixin(mixin.id)
    assert len(list(schema.mixins)) == 0
    assert schema.requires_validation


def test_validate_throws_if_mixin_not_resolved():
    schema = Schema()
    record = schema.create_record("http://example.org/record/foo", "http://example.org/def/Foo", "Foo")
    record.add_mixin("http://example.org/mixin/bar")
    with pytest.raises(SchemaValidationException) as exc_info:
        schema.validate()
    ire = exc_info.value.validation_errors[0]
    assert isinstance(ire, InvalidRecordException)
    assert isinstance(ire.cause, MixinNotFoundException)


def test_validate_throws_on_circular_inheritance():
    schema = Schema()
    record_a = schema.create_record("http://example.org/record/A", "http://example.org/def/A", "A")
    record_b = schema.create_record("http://example.org/record/B", "http://example.org/def/B", "B")
    record_c = schema.create_record("http://example.org/record/C", "http://example.org/def/C", "C")
    record_b.set_parent("http://example.org/record/A")
    record_c.set_parent("http://example.org/record/B")
    schema.validate()
    record_a.set_parent("http://example.org/record/C")
    with pytest.raises(SchemaValidationException) as exc_info:
        schema.validate()
    e = exc_info.value.validation_errors[0]
    assert isinstance(e, InvalidRecordException)
    assert isinstance(e.cause, CircularInheritanceException)


def test_validate_throws_on_incompatible_value_range():
    schema = Schema()
    record_a = schema.create_record("http://example.org/record/A", "http://example.org/def/A", "A")
    record_a.create_literal_property("age", "http://example.org/def/age", required=True).add_constraint(
        XSD + "integer", min_inclusive="18", max_inclusive="35"
    )
    record_b = schema.create_record("http://example.org/record/B", "http://example.org/def/B", "B")
    record_b.create_literal_property("age", "http://example.org/def/age", required=True).add_constraint(
        XSD + "integer", min_exclusive="65"
    )

    # Should be valid before inheritance is added
    schema.validate()

    record_b.set_parent("http://example.org/record/A")
    with pytest.raises(SchemaValidationException) as exc_info:
        schema.validate()
    e = exc_info.value.validation_errors[0]
    assert isinstance(e, InvalidRecordException)
    assert isinstance(e.cause, IncompatiblePropertyException)
    assert isinstance(e.cause.cause, IncompatibleRangeException)


def test_validate_throws_on_inherited_property_clash():
    schema = Schema()
    record_a = schema.create_record("http://example.org/record/A", "http://example.org/def/A", "A")
    record_a.create_literal_property("age", "http://example.org/def/age", required=True).add_constraint(
        XSD + "integer", min_inclusive="18", max_inclusive="35"
    )
    record_b = schema.create_record("http://example.org/record/B", "http://example.org/def/B", "B")
    record_b.create_literal_property("age", "https://schema.org/age", required=True).add_constraint(
        XSD + "integer", min_exclusive="65"
    )

    # Should be valid before inheritance is added
    schema.validate()

    record_b.set_parent("http://example.org/record/A")
    with pytest.raises(SchemaValidationException) as exc_info:
        schema.validate()
    e = exc_info.value.validation_errors[0]
    assert isinstance(e, InvalidRecordException)
    assert isinstance(e.cause, PropertyClashException)


def test_validate_throws_on_mixin_property_clash():
    schema = Schema()
    record_a = schema.create_record("http://example.org/record/A", "http://example.org/def/A", "A")
    mixin_a = schema.create_mixin("http://example.org/mixin/A")
    mixin_b = schema.create_mixin("http://example.org/mixin/B")
    mixin_a.create_literal_property("age", "http://example.org/def/age", required=True).add_constraint(XSD + "integer")
    mixin_b.create_literal_property("age", "http://example.org/def/age", required=True).add_constraint(XSD + "integer")
    record_a.add_mixin("http://example.org/mixin/A")
    record_a.add_mixin(mixin_b.id)
    assert len(list(record_a.mixins)) == 2
    with pytest.raises(SchemaValidationException) as exc_info:
        schema.validate()
    inner = exc_info.value.validation_errors[0]
    assert isinstance(inner, InvalidRecordException)
    mpce = inner.cause
    assert isinstance(mpce, MixinPropertyClashException)
    assert mpce.clash_property == "shortCode"
    assert mpce.clash_value == "age"
    assert mpce.mixin_a == mixin_a
    assert mpce.mixin_b == mixin_b


def test_validate_throws_on_invalid_record_short_code():
    schema = Schema()
    schema.create_record("http://example.org/record/A", "http://example.org/def/A", "1A")
    with pytest.raises(SchemaValidationException) as exc_info:
        schema.validate()
    inner = exc_info.value.validation_errors[0]
    assert isinstance(inner, InvalidRecordException)
    assert isinstance(inner.cause, InvalidShortCodeException)


def test_validate_throws_on_invalid_literal_property_short_code():
    schema = Schema()
    record_a = schema.create_record("http://example.org/record/A", "http://example.org/def/A", "A")
    record_a.create_literal_property("123", "http://example.org/def/123").add_constraint(XSD + "string")
    with pytest.raises(SchemaValidationException) as exc_info:
        schema.validate()
    inner = exc_info.value.validation_errors[0]
    ire = inner
    assert isinstance(ire, InvalidRecordException)
    ipe = ire.cause
    assert isinstance(ipe, InvalidPropertyException)
    assert isinstance(ipe.cause, InvalidShortCodeException)


def test_validate_throws_on_invalid_record_property_short_code():
    schema = Schema()
    record_a = schema.create_record("http://example.org/record/A", "http://example.org/def/A", "A")
    record_a.create_record_property("123", "http://example.org/def/123").add_constraint(record_a.id)
    with pytest.raises(SchemaValidationException) as exc_info:
        schema.validate()
    inner = exc_info.value.validation_errors[0]
    ire = inner
    assert isinstance(ire, InvalidRecordException)
    ipe = ire.cause
    assert isinstance(ipe, InvalidPropertyException)
    assert isinstance(ipe.cause, InvalidShortCodeException)


def test_validate_throws_on_unresolved_record_constraint():
    schema = Schema()
    record_a = schema.create_record("http://example.org/record/A", "http://example.org/def/A", "A")
    p = record_a.create_record_property("hasB", "http://example.org/hasB")
    p.add_constraint("http://example.org/record/B")
    with pytest.raises(SchemaValidationException) as exc_info:
        schema.validate()
    inner = exc_info.value.validation_errors[0]
    ire = inner
    assert isinstance(ire, InvalidRecordException)
    ipe = ire.cause
    assert isinstance(ipe, InvalidPropertyException)
    irce = ipe.cause
    assert isinstance(irce, InvalidRecordConstraintException)
    assert isinstance(irce.cause, RecordNotFoundException)


def test_validate_throws_on_two_records_with_same_short_code_and_different_ids():
    schema = Schema()
    schema.create_record("http://example.org/record/A", "http://example.org/def/A", "A")
    schema.create_record("http://example.org/record/A2", "http://example.org/def/A2", "A")
    with pytest.raises(SchemaValidationException) as exc_info:
        schema.validate()
    inner = exc_info.value.validation_errors[0]
    assert isinstance(inner, RecordShortCodeClashException)


def test_validate_throws_on_incompatible_reverse_property():
    schema = Schema()
    record_a = schema.create_record("http://example.org/record/A", "http://example.org/def/A", "A")
    record_b = schema.create_record("http://example.org/record/B", "http://example.org/def/B", "B")
    record_c = schema.create_record("http://example.org/record/C", "http://example.org/def/C", "C")
    p = record_b.create_record_property("hasC", "http://example.org/hasC")
    p.add_constraint(record_c.id)
    invalid_reverse_property = record_a.create_record_property(
        "isAOf", "http://example.org/hasC", reversed=True
    )
    invalid_reverse_property.add_constraint(record_b.id)
    with pytest.raises(SchemaValidationException) as exc_info:
        schema.validate()
    inner = exc_info.value.validation_errors[0]
    ire = inner
    assert isinstance(ire, InvalidRecordException)
    ipe = ire.cause
    assert isinstance(ipe, InvalidPropertyException)
    assert isinstance(ipe.cause, InvalidReversePropertyRangeException)


def test_validate_does_not_throw_if_forward_property_is_open():
    schema = Schema()
    record_a = schema.create_record("http://example.org/record/A", "http://example.org/def/A", "A")
    record_b = schema.create_record("http://example.org/record/B", "http://example.org/def/B", "B")
    record_b.create_record_property("hasC", "http://example.org/hasC")
    invalid_reverse_property = record_a.create_record_property(
        "isAOf", "http://example.org/hasC", reversed=True
    )
    invalid_reverse_property.add_constraint(record_b.id)
    schema.validate()


def test_validate_does_not_throw_if_forward_property_range_includes_reverse_property_record_as_subclass():
    schema = Schema()
    record_a = schema.create_record("http://example.org/record/A", "http://example.org/def/A", "A")
    record_b = schema.create_record("http://example.org/record/B", "http://example.org/def/B", "B")
    record_c = schema.create_record("http://example.org/record/C", "http://example.org/def/C", "C")
    record_a.set_parent(record_c.id)
    p = record_b.create_record_property("hasC", "http://example.org/hasC")
    p.add_constraint(record_c.id)
    invalid_reverse_property = record_a.create_record_property(
        "isAOf", "http://example.org/hasC", reversed=True
    )
    invalid_reverse_property.add_constraint(record_b.id)
    schema.validate()


def test_validate_does_not_throw_on_directly_compatible_reverse_property():
    schema = Schema()
    record_a = schema.create_record("http://example.org/record/A", "http://example.org/def/A", "A")
    record_b = schema.create_record("http://example.org/record/B", "http://example.org/def/B", "B")
    p = record_b.create_record_property("hasA", "http://example.org/hasA")
    p.add_constraint(record_a.id)
    invalid_reverse_property = record_a.create_record_property(
        "isAOf", "http://example.org/hasA", reversed=True
    )
    invalid_reverse_property.add_constraint(record_b.id)
    schema.validate()


def test_validate_throws_if_property_override_changes_reversed_flag():
    schema = Schema()
    record_a = schema.create_record("http://example.org/record/A", "http://example.org/def/A", "A")
    record_b = schema.create_record("http://example.org/record/B", "http://example.org/def/B", "B")
    schema.create_record("http://example.org/record/C", "http://example.org/def/C", "C")
    record_a.set_parent(record_b.id)
    record_b.create_record_property("hasC", "http://example.org/p", reversed=True)
    record_a.create_record_property("hasC", "http://example.org/p", reversed=False)
    with pytest.raises(SchemaValidationException) as exc_info:
        schema.validate()
    inner = exc_info.value.validation_errors[0]
    ire = inner
    assert isinstance(ire, InvalidRecordException)
    assert isinstance(ire.cause, IncompatiblePropertyException)


def test_clone_succeeds_when_a_type_is_used_before_declaration():
    schema = load_schema("use_before_decl.yaml")
    clone = schema.clone()
    clone_foo = schema.resolve_record("Foo")
    assert len(list(clone_foo.effective_properties)) == 1
    has_bar = list(clone_foo.effective_properties)[0]
    assert isinstance(has_bar, RecordProperty)
    assert has_bar.constraints[0].record.short_code == "Bar"
    clone.validate()