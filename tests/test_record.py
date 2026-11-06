"""Port of the Kotlin ``RecordTests``."""

from __future__ import annotations

import pytest

from record_spec.model import RecordProperty, Schema
from record_spec.values import XSD


def test_record_creation():
    schema = Schema()
    schema.create_record("http://example.org/record/foo", "http://example.org/def/Foo", "Foo")
    assert schema.requires_validation
    assert len(list(schema.records)) == 1


def test_add_empty_mixin():
    schema = Schema()
    record = schema.create_record("http://example.org/record/foo", "http://example.org/def/Foo", "Foo")
    mixin = schema.create_mixin("http://example.org/mixin/bar")
    record.add_mixin(mixin.id)
    schema.validate()
    assert len(list(record.mixins)) == 1


def test_schema_validation_throws_if_mixin_does_not_exist():
    """Port of the upstream #63 change: invalid mixin references are only
    validated by Schema.validate()."""
    from record_spec.exceptions import InvalidRecordException, MixinNotFoundException, SchemaValidationException

    schema = Schema()
    record = schema.create_record("http://example.org/record/foo", "http://example.org/def/Foo", "Foo")
    record.add_mixin("http://example.org/mixin/bar")
    with pytest.raises(SchemaValidationException) as exc_info:
        schema.validate()
    assert len(exc_info.value.validation_errors) == 1
    invalid_record = exc_info.value.validation_errors[0]
    assert isinstance(invalid_record, InvalidRecordException)
    assert isinstance(invalid_record.cause, MixinNotFoundException)


def test_add_mixin_has_no_effect_if_mixin_already_added():
    schema = Schema()
    record = schema.create_record("http://example.org/record/foo", "http://example.org/def/Foo", "Foo")
    mixin = schema.create_mixin("http://example.org/mixin/bar")
    record.add_mixin(mixin.id)
    schema.validate()
    assert len(list(record.mixins)) == 1
    record.add_mixin(mixin.id)
    assert len(list(record.mixins)) == 1


def test_add_mixin_extends_effective_properties():
    schema = Schema()
    record = schema.create_record("http://example.org/record/foo", "http://example.org/def/Foo", "Foo")
    mixin = schema.create_mixin("http://example.org/mixin/bar")
    mixin.create_literal_property("bar", "http://example.org/def/bar").add_constraint(XSD + "string")
    record.add_mixin(mixin.id)
    schema.validate()
    assert len(list(record.mixins)) == 1
    props = list(record.effective_properties)
    assert len(props) == 1
    assert props[0].short_code == "bar"


def test_remove_mixin_succeeds_if_mixin_not_defined():
    schema = Schema()
    record = schema.create_record("http://example.org/record/foo", "http://example.org/def/Foo", "Foo")
    mixin_bar = schema.create_mixin("http://example.org/mixin/bar")
    mixin_baz = schema.create_mixin("http://example.org/mixin/baz")
    record.add_mixin(mixin_bar.id)
    record.remove_mixin(mixin_baz.id)


def test_remove_mixin_updates_effective_properties():
    schema = Schema()
    record = schema.create_record("http://example.org/record/foo", "http://example.org/def/Foo", "Foo")
    mixin = schema.create_mixin("http://example.org/mixin/bar")
    mixin.create_literal_property("bar", "http://example.org/def/bar").add_constraint(XSD + "string")
    record.add_mixin(mixin.id)
    schema.validate()
    assert len(list(record.effective_properties)) == 1
    record.remove_mixin(mixin.id)
    assert len(list(record.effective_properties)) == 0


def test_set_parent_extends_effective_properties():
    schema = Schema()
    record = schema.create_record("http://example.org/record/foo", "http://example.org/def/Foo", "Foo")
    base = schema.create_record("http://example.org/record/thing", "http://example.org/def/Thing", "Thing")
    base.create_literal_property("label", "http://example.org/def/label").add_constraint(XSD + "string")
    record.set_parent(base.id)
    schema.validate()
    props = list(record.effective_properties)
    assert len(props) == 1
    assert props[0].short_code == "label"


def test_set_parent_provides_base_properties():
    schema = Schema()
    record = schema.create_record("http://example.org/record/foo", "http://example.org/def/Foo", "Foo")
    record.create_literal_property("label", "http://example.org/def/label", required=True).add_constraint(
        XSD + "string"
    )
    base = schema.create_record("http://example.org/record/thing", "http://example.org/def/Thing", "Thing")
    base.create_literal_property("label", "http://example.org/def/label").add_constraint(XSD + "string")
    record.set_parent(base.id)
    schema.validate()
    base_props = list(base.effective_properties)
    assert len(base_props) == 1
    assert base_props[0].short_code == "label"
    assert not base_props[0].required

    props = list(record.effective_properties)
    assert len(props) == 1
    assert props[0].short_code == "label"
    assert props[0].required


def test_set_parent_to_null_updates_effective_properties():
    schema = Schema()
    record = schema.create_record("http://example.org/record/foo", "http://example.org/def/Foo", "Foo")
    base = schema.create_record("http://example.org/record/thing", "http://example.org/def/Thing", "Thing")
    base.create_literal_property("label", "http://example.org/def/label").add_constraint(XSD + "string")
    record.set_parent(base.id)
    props_before_remove = list(record.effective_properties)
    record.set_parent(None)
    properties_after_remove = list(record.effective_properties)
    assert len(props_before_remove) == 1
    assert len(properties_after_remove) == 0


def test_parent_record_mixins_extend_effective_properties():
    schema = Schema()
    record = schema.create_record("http://example.org/record/foo", "http://example.org/def/Foo", "Foo")
    base = schema.create_record("http://example.org/record/thing", "http://example.org/def/Thing", "Thing")
    base.create_literal_property("label", "http://example.org/def/label").add_constraint(XSD + "string")
    mixin = schema.create_mixin("http://example.org/mixin/bar")
    mixin.create_literal_property("bar", "http://example.org/def/bar").add_constraint(XSD + "string")
    base.add_mixin(mixin.id)
    record.set_parent(base.id)
    schema.validate()
    props = list(record.effective_properties)
    assert len(props) == 2
    assert any(p.short_code == "bar" for p in props)
    assert any(p.short_code == "label" for p in props)


def test_create_literal_property_fails_when_new_property_clashes_on_the_same_record():
    """Port of the upstream #60 regression tests."""
    from record_spec.exceptions import PropertyUriExistsException, ShortCodeExistsException

    schema = Schema()
    record = schema.create_record("http://example.org/record/foo", "http://example.org/def/Foo", "Foo")
    record.create_literal_property("test", "http://example.org/def/test")
    with pytest.raises(ShortCodeExistsException):
        record.create_literal_property("test", "http://example.org/def/test")
    with pytest.raises(ShortCodeExistsException):
        record.create_literal_property("test", "http://example.org/def/test2")
    with pytest.raises(PropertyUriExistsException):
        record.create_literal_property("test2", "http://example.org/def/test")


def test_create_record_property_fails_when_new_property_clashes_on_the_same_record():
    from record_spec.exceptions import PropertyUriExistsException, ShortCodeExistsException

    schema = Schema()
    record = schema.create_record("http://example.org/record/foo", "http://example.org/def/Foo", "Foo")
    record.create_record_property("test", "http://example.org/def/test")
    with pytest.raises(ShortCodeExistsException):
        record.create_record_property("test", "http://example.org/def/test")
    with pytest.raises(ShortCodeExistsException):
        record.create_record_property("test", "http://example.org/def/test2")
    with pytest.raises(PropertyUriExistsException):
        record.create_record_property("test2", "http://example.org/def/test")


def test_clone_copies_documentation():
    """Port of the Kotlin #58 regression test: record, mixin and property
    documentation survives a clone."""
    from record_spec.model import LangString

    schema = Schema()
    record = schema.create_record("http://example.org/record/foo", "http://example.org/def/Foo", "Foo")
    record.label.append(LangString("Foo Record", "en"))
    record.summary.append(LangString("Foo Summary", "en"))
    record.description.append(LangString("Foo Description", "en"))
    label = record.create_literal_property("label", "http://example.org/def/label")
    label.label.append(LangString("label Label", "en"))
    label.summary.append(LangString("label Summary", "en"))
    label.description.append(LangString("label Description", "en"))
    ref = record.create_record_property("ref", "http://example.org/def/ref")
    ref.label.append(LangString("ref Label", "en"))
    ref.summary.append(LangString("ref Summary", "en"))
    ref.description.append(LangString("ref Description", "en"))

    target_schema = Schema()
    target_record = record.clone(target_schema)
    assert target_record.label[0] == LangString("Foo Record", "en")
    assert target_record.summary[0] == LangString("Foo Summary", "en")
    assert target_record.description[0] == LangString("Foo Description", "en")
    target_prop = target_record.get_property("label")
    assert target_prop is not None
    assert target_prop.label[0] == LangString("label Label", "en")
    assert target_prop.summary[0] == LangString("label Summary", "en")
    assert target_prop.description[0] == LangString("label Description", "en")
    target_ref = target_record.get_property("ref")
    assert target_ref is not None
    assert target_ref.label[0] == LangString("ref Label", "en")
    assert target_ref.summary[0] == LangString("ref Summary", "en")
    assert target_ref.description[0] == LangString("ref Description", "en")


def test_all_parents_and_descendents():
    schema = Schema()
    base = schema.create_record("http://example.org/record/Base", "http://example.org/def/Base", "Base")
    derived = schema.create_record("http://example.org/record/Derived", "http://example.org/def/Derived", "Derived")
    derived.set_parent(base.id)
    assert derived.has_parent(base.id)
    assert not base.has_parent(derived.id)
    assert derived in base.all_descendents()
    assert derived in base.all_descendents_and_self() or base in base.all_descendents_and_self()
    assert [r.id for r in derived.all_parents()] == [base.id]


def test_gather_nested_records():
    schema = Schema()
    foo = schema.create_record("http://example.org/record/Foo", "http://example.org/def/Foo", "Foo")
    bar = schema.create_record("http://example.org/record/Bar", "http://example.org/def/Bar", "Bar")
    p = foo.create_record_property("hasBar", "http://example.org/def/hasBar", nested=True)
    p.add_constraint(bar.id)
    nested = foo.gather_nested_records()
    assert foo in nested and bar in nested


def test_get_property_by_short_code_or_uri():
    schema = Schema()
    foo = schema.create_record("http://example.org/record/Foo", "http://example.org/def/Foo", "Foo")
    prop = foo.create_literal_property("label", "http://example.org/def/label")
    assert foo.get_property("label") is prop
    assert foo.get_property("http://example.org/def/label") is prop
    assert isinstance(prop, object)
    assert not isinstance(prop, RecordProperty)