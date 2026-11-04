"""Port of the Kotlin ``SchemaMergeTests`` and ``YamlDeserializationTests``/``YamlSerializationTests``."""

from __future__ import annotations

import pytest
from helpers import (
    load_schema,
    load_schema_def,
    load_yaml,
    normalize,
    schema_to_tree,
)

from record_spec.model import LangString, LiteralProperty, RecordProperty
from record_spec.serde import SchemaDef
from record_spec.values import XSD

MERGE_CASES = [
    ("A.yaml", "B.yaml", "A_B.yaml"),
    ("A.yaml", "C.yaml", "A_C.yaml"),
    ("A.yaml", "D.yaml", "A_D.yaml"),
    ("A.yaml", "E.yaml", "A_E.yaml"),
    ("A.yaml", "F.yaml", "A_F.yaml"),
]


@pytest.mark.parametrize(("schema_a_resource", "schema_b_resource", "expected_resource"), MERGE_CASES)
def test_schema_merge(schema_a_resource: str, schema_b_resource: str, expected_resource: str):
    schema_a = load_schema(f"merge/{schema_a_resource}")
    schema_b = load_schema(f"merge/{schema_b_resource}")
    expected_yaml = load_yaml(f"merge/{expected_resource}")

    schema_a.merge(schema_b)
    actual_yaml = schema_to_tree(schema_a)
    assert normalize(actual_yaml) == normalize(expected_yaml)


# ---- YamlDeserializationTests ----


def test_deser01():
    schema_def = load_schema_def("deser01.yaml")
    assert schema_def.identifier == "http://example.org/deser01"
    assert schema_def.base == "http://example.org/deser01/"
    prefix_ex = next((p for p in schema_def.prefixes or [] if p.prefix == "ex"), None)
    assert prefix_ex is not None
    assert prefix_ex.uri == "http://example.org/def/"
    prefix_xsd = next((p for p in schema_def.prefixes or [] if p.prefix == "xsd"), None)
    assert prefix_xsd is not None
    assert prefix_xsd.uri == "http://www.w3.org/2001/XMLSchema#"
    assert schema_def.mixins is not None
    mixin_def = schema_def.mixins["Bar"]
    assert mixin_def is not None
    assert mixin_def.label[0].value == "Bar"
    assert mixin_def.label[0].language is None
    assert mixin_def.summary[0].value == "Summary Text"
    assert mixin_def.summary[0].language is None
    assert mixin_def.description[0].value == "Text with a language"
    assert mixin_def.description[0].language == "en"
    mixin_baz = schema_def.mixins["Baz"]
    assert mixin_baz is not None
    assert schema_def.records is not None
    record = schema_def.records["Foo"]
    assert record is not None
    assert record.class_uri == "ex:Foo"
    assert record.short_code == "Foo"


def _assert_literal_constraint(
    constraint,
    datatype: str,
    pattern: str | None = None,
    min_inclusive: str | None = None,
    max_inclusive: str | None = None,
    min_exclusive: str | None = None,
    max_exclusive: str | None = None,
    in_: list[str] | None = None,
):
    assert constraint.datatype == datatype
    assert constraint.pattern == pattern
    assert constraint.min_inclusive == min_inclusive
    assert constraint.max_inclusive == max_inclusive
    assert constraint.min_exclusive == min_exclusive
    assert constraint.max_exclusive == max_exclusive
    assert constraint.in_ == in_


def test_literals01():
    schema = load_schema("literals01.yaml")
    schema.validate()
    record = schema.resolve_record("Foo")
    assert record is not None
    assert len(list(record.effective_properties)) == 5
    with_pattern = record.get_property("withPattern")
    assert isinstance(with_pattern, LiteralProperty)
    _assert_literal_constraint(
        constraint=with_pattern.constraints[0],
        datatype=XSD + "string",
        pattern="^[a-zA-Z][0-9a-zA-Z]*$",
    )
    with_inclusive_range = record.get_property("withInclusiveRange")
    assert isinstance(with_inclusive_range, LiteralProperty)
    _assert_literal_constraint(
        constraint=with_inclusive_range.constraints[0],
        datatype=XSD + "integer",
        min_inclusive="0",
        max_inclusive="10",
    )
    with_exclusive_range = record.get_property("withExclusiveRange")
    assert isinstance(with_exclusive_range, LiteralProperty)
    _assert_literal_constraint(
        constraint=with_exclusive_range.constraints[0],
        datatype=XSD + "integer",
        min_exclusive="-10",
        max_exclusive="10",
    )
    with_enumeration = record.get_property("withEnumeration")
    assert isinstance(with_enumeration, LiteralProperty)
    _assert_literal_constraint(
        constraint=with_enumeration.constraints[0],
        datatype=XSD + "string",
        in_=["RED", "GREEN", "BLUE"],
    )
    with_union = record.get_property("withUnion")
    assert isinstance(with_union, LiteralProperty)
    _assert_literal_constraint(constraint=with_union.constraints[0], datatype=XSD + "date")
    _assert_literal_constraint(constraint=with_union.constraints[1], datatype=XSD + "dateTime")


def _assert_lang_string(container, value: str, language: str | None = None):
    assert LangString(value, language) in list(container), (
        f"Expected LangString({value!r}, {language!r}) in {[str(ls) for ls in container]}"
    )


def test_simple_record():
    schema = load_schema("simpleRecord.yaml")
    schema.validate()
    record = schema.resolve_record("Simple")
    assert record is not None
    assert record.id == "http://test.epimorphics.com/record-spec/Simple"
    _assert_lang_string(record.label, "Simple")
    _assert_lang_string(record.label, "Simple Record")
    _assert_lang_string(record.summary, "A simple record.")
    _assert_lang_string(record.summary, "Un record simple.", "fr")
    _assert_lang_string(record.description, "A simple record.", "en")
    _assert_lang_string(record.description, "Un record simple.", "fr")
    assert len(list(record.effective_properties)) == 3
    assert record.parent is None
    assert len(list(record.mixins)) == 0
    label = record.get_property("label")
    assert isinstance(label, LiteralProperty)
    _assert_lang_string(label.label, "Label", "en")
    _assert_lang_string(label.summary, "The display label for this item.", "en")
    assert label.short_code == "label"
    assert label.property_uri == "http://www.w3.org/2000/01/rdf-schema#label"
    assert label.required
    assert not label.repeatable
    _assert_literal_constraint(constraint=label.constraints[0], datatype=XSD + "string")
    related = record.get_property("related")
    assert isinstance(related, RecordProperty)
    _assert_lang_string(related.label, "Related To")
    assert related.short_code == "related"
    assert related.property_uri == "http://test.epimorphics.com/record-spec/def/related"
    assert not related.nested
    assert not related.required
    assert related.repeatable
    assert related.constraints[0].record.compact_id == "Simple"
    has_part = record.get_property("hasPart")
    assert isinstance(has_part, RecordProperty)
    assert has_part.nested
    assert not has_part.required
    assert has_part.repeatable
    assert related.constraints[0].record.compact_id == "Simple"


def test_inheritance01():
    schema = load_schema("inheritance01.yaml")
    schema.validate()
    base = schema.resolve_record("Base")
    derived_a = schema.resolve_record("DerivedA")
    derived_b = schema.resolve_record("DerivedB")
    assert base is not None
    assert derived_a is not None
    assert derived_b is not None
    assert derived_a.has_parent(base.id)
    assert derived_b.has_parent(derived_a.id)
    assert derived_b.has_parent(base.id)
    assert not derived_a.has_parent(derived_b.id)
    assert not base.has_parent(derived_a.id)

    assert len(list(base.effective_properties)) == 3
    assert len(list(derived_a.effective_properties)) == 3
    assert len(list(derived_b.effective_properties)) == 3


def test_mixins01():
    schema = load_schema("mixins01.yaml")
    schema.validate()
    record_a = schema.resolve_record("RecordA")
    record_b = schema.resolve_record("RecordB")
    record_c = schema.resolve_record("RecordC")
    record_d = schema.resolve_record("RecordD")
    record_e = schema.resolve_record("RecordE")
    assert record_a is not None
    assert record_b is not None
    assert record_c is not None
    assert record_d is not None
    assert record_e is not None
    assert len(list(record_a.effective_properties)) == 1
    assert len(list(record_b.effective_properties)) == 2
    assert len(list(record_c.effective_properties)) == 3
    assert len(list(record_d.effective_properties)) == 3
    assert len(list(record_e.effective_properties)) == 3


def test_property_maps():
    schema = load_schema("propertyMaps.yaml")
    schema.validate()
    foo = schema.resolve_record("Foo")
    bar = schema.resolve_record("Bar")
    baz = schema.resolve_record("Baz")
    assert foo is not None
    assert bar is not None
    assert baz is not None
    foo_map = baz.get_property("fooMap")
    assert isinstance(foo_map, RecordProperty)
    assert foo_map.property_mapping is not None
    assert foo_map.property_mapping.key_property == "identifier"
    bar_map = baz.get_property("barMap")
    assert isinstance(bar_map, RecordProperty)
    assert bar_map.property_mapping is not None
    assert bar_map.property_mapping.key_property == "notation"


def test_imports():
    schema = load_schema("imports.yaml")
    resource_base = schema.base_uri
    assert resource_base is not None
    schema.validate()
    imports = list(schema.imports)
    assert len(imports) == 2
    from urllib.parse import urljoin

    assert imports[0] == urljoin(resource_base, "deser01.yaml")
    assert imports[1] == urljoin(resource_base, "inheritance01.yaml")


def test_extensions():
    schema_def = load_schema_def("extensions.yaml")
    assert schema_def.extensions is not None
    assert len(schema_def.extensions) == 2
    assert isinstance(schema_def.extensions[0], dict)
    assert schema_def.records is not None
    record = schema_def.records["Foo"]
    assert record is not None
    assert record.extensions is not None
    assert len(record.extensions) == 2
    assert isinstance(record.extensions[0], dict)
    assert record.properties is not None
    prop = record.properties["foo"]
    assert prop is not None
    assert prop.extensions is not None
    assert len(prop.extensions) == 2
    assert isinstance(prop.extensions[0], dict)
    assert schema_def.mixins is not None
    mixin = schema_def.mixins["Bar"]
    assert mixin is not None
    assert mixin.extensions is not None
    assert len(mixin.extensions) == 2
    assert isinstance(mixin.extensions[0], dict)


def test_schema_description():
    schema = load_schema("schema_description.yaml")
    assert schema.description is not None
    assert len(schema.description) == 1
    _assert_lang_string(
        schema.description,
        "A subset of the Agora Catalog data model, adapted for testing purposes.",
        "en",
    )


# ---- YamlSerializationTests ----


def test_serialize_extensions():
    obj = {
        "type": "http://example.org/extensions/MyExtension",
        "someProperty": "foo",
    }
    schema_def = SchemaDef(extensions=[obj])
    expect_tree = {"extensions": [{"type": "http://example.org/extensions/MyExtension", "someProperty": "foo"}]}
    actual_tree = schema_def.to_dict()
    assert normalize(actual_tree) == normalize(expect_tree)