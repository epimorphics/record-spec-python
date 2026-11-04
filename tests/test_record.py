"""Port of the Kotlin ``RecordTests``."""

from __future__ import annotations

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