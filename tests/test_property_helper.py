"""Port of the Kotlin ``PropertyHelperTests``."""

from __future__ import annotations

import pytest

from record_spec.exceptions import (
    IncompatiblePropertyException,
    IncompatibleRangeException,
    NoComparatorException,
    PropertyClashException,
)
from record_spec.model import LiteralProperty, RecordProperty, Schema
from record_spec.model.property_helper import PropertyHelper
from record_spec.values import XSD


def test_combine_property_lists_throws_if_properties_match_in_short_code_and_not_uri():
    list_a = [LiteralProperty("foo", "http://example.org/foo")]
    list_b = [LiteralProperty("foo", "http://example.org/foobar")]
    schema = Schema()
    helper = PropertyHelper(schema)
    with pytest.raises(PropertyClashException) as exc_info:
        list(helper.combine_property_lists(list_a, list_b))
    assert exc_info.value.property_a == list_a[0]
    assert exc_info.value.property_b == list_b[0]


def test_combine_property_lists_throws_if_properties_match_in_uri_and_not_short_code():
    list_a = [LiteralProperty("foo", "http://example.org/foo")]
    list_b = [LiteralProperty("foobar", "http://example.org/foo")]
    schema = Schema()
    helper = PropertyHelper(schema)
    with pytest.raises(PropertyClashException) as exc_info:
        list(helper.combine_property_lists(list_a, list_b))
    assert exc_info.value.property_a == list_a[0]
    assert exc_info.value.property_b == list_b[0]


def test_combine_property_lists_yields_properties_with_no_match_in_other_list():
    list_a = [LiteralProperty("foo", "http://example.org/foo")]
    list_b = [LiteralProperty("bar", "http://example.org/bar")]
    schema = Schema()
    helper = PropertyHelper(schema)
    combined = list(helper.combine_property_lists(list_a, list_b))
    assert len(combined) == 2
    assert combined[0] == list_a[0]
    assert combined[1] == list_b[0]


def test_combine_property_lists_throws_if_properties_differ_in_kind():
    schema = Schema()
    helper = PropertyHelper(schema)
    list_a = [LiteralProperty("foo", "http://example.org/foo")]
    list_b = [RecordProperty(schema, "foo", "http://example.org/foo")]
    with pytest.raises(IncompatiblePropertyException) as exc_info:
        list(helper.combine_property_lists(list_a, list_b))
    assert exc_info.value.property_a == list_a[0]
    assert exc_info.value.property_b == list_b[0]


def test_combine_property_lists_narrows_cardinality():
    schema = Schema()
    helper = PropertyHelper(schema)
    list_a = [
        LiteralProperty("foo", "http://example.org/foo", repeatable=True),
        LiteralProperty("bar", "http://example.org/bar", required=True),
        RecordProperty(schema, "baz", "http://example.org/baz", repeatable=True),
        RecordProperty(schema, "qux", "http://example.org/qux", required=True),
    ]
    list_b = [
        LiteralProperty("foo", "http://example.org/foo", repeatable=False),
        LiteralProperty("bar", "http://example.org/bar", required=False),
        RecordProperty(schema, "baz", "http://example.org/baz", repeatable=False),
        RecordProperty(schema, "qux", "http://example.org/qux", required=False),
    ]
    results = list(helper.combine_property_lists(list_a, list_b))
    result_foo = next((p for p in results if p.short_code == "foo"), None)
    result_bar = next((p for p in results if p.short_code == "bar"), None)
    result_baz = next((p for p in results if p.short_code == "baz"), None)
    result_qux = next((p for p in results if p.short_code == "qux"), None)
    assert result_foo is not None
    assert result_bar is not None
    assert result_baz is not None
    assert result_qux is not None
    assert not result_foo.repeatable
    assert result_bar.required
    assert not result_baz.repeatable
    assert result_qux.required


def test_combine_property_lists_throws_if_combining_nested_and_reference_properties():
    schema = Schema()
    helper = PropertyHelper(schema)
    list_a = [RecordProperty(schema, "foo", "http://example.org/foo", nested=True)]
    list_b = [RecordProperty(schema, "foo", "http://example.org/foo", nested=False)]
    with pytest.raises(IncompatiblePropertyException):
        list(helper.combine_property_lists(list_a, list_b))


def test_combine_property_lists_throws_if_literal_properties_have_no_compatible_range():
    schema = Schema()
    helper = PropertyHelper(schema)
    pa = LiteralProperty("foo", "http://example.org/foo")
    pa.add_constraint(XSD + "integer", min_inclusive="18", max_inclusive="35")
    pb = LiteralProperty("foo", "http://example.org/foo")
    pb.add_constraint(XSD + "integer", min_inclusive="65")

    with pytest.raises(IncompatiblePropertyException) as exc_info:
        list(helper.combine_property_lists([pa], [pb]))
    assert exc_info.value.cause is not None
    assert isinstance(exc_info.value.cause, IncompatibleRangeException)


def test_combine_property_lists_combines_pattern_constraint():
    schema = Schema()
    helper = PropertyHelper(schema)
    pa = LiteralProperty("foo", "http://example.org/foo")
    pa.add_constraint(XSD + "string", pattern="foo")
    pb = LiteralProperty("foo", "http://example.org/foo")
    pb.add_constraint(XSD + "string", pattern="bar")
    result = list(helper.combine_property_lists([pa], [pb]))
    result_lit = result[0]
    assert isinstance(result_lit, LiteralProperty)
    assert result_lit.constraints[0].pattern == "(?=foo)(?=bar)"


def test_combine_property_lists_intersects_allowed_values():
    schema = Schema()
    helper = PropertyHelper(schema)
    schema.create_record("http://example.org/record/Foo", "http://example.org/Foo", "Foo")
    pa = LiteralProperty("foo", "http://example.org/foo")
    pa.add_constraint(XSD + "string", in_=["foo", "baz"])
    pb = LiteralProperty("foo", "http://example.org/foo")
    pb.add_constraint(XSD + "string", in_=["bar", "baz"])

    pc = RecordProperty(schema, "foo", "http://example.org/foo")
    pc.add_constraint("http://example.org/record/Foo", ["http://example.org/foo", "http://example.org/baz"])
    pd = RecordProperty(schema, "foo", "http://example.org/foo")
    pd.add_constraint("http://example.org/record/Foo", ["http://example.org/bar", "http://example.org/baz"])

    result = list(helper.combine_property_lists([pa], [pb]))
    result_lit = result[0]
    assert isinstance(result_lit, LiteralProperty)
    assert result_lit.constraints[0].in_ == ["baz"]

    result2 = list(helper.combine_property_lists([pc], [pd]))
    result_rec = result2[0]
    assert isinstance(result_rec, RecordProperty)
    assert result_rec.constraints[0].in_ == ["http://example.org/baz"]


def test_combine_property_lists_narrows_record_property_range():
    schema = Schema()
    helper = PropertyHelper(schema)
    schema.create_record("http://example.org/record/Base", "http://example.org/Base", "Base")
    derived = schema.create_record("http://example.org/record/Derived", "http://example.org/Derived", "Derived")
    derived.set_parent("http://example.org/record/Base")

    pa = RecordProperty(schema, "foo", "http://example.org/foo")
    pa.add_constraint("http://example.org/record/Base")
    pb = RecordProperty(schema, "foo", "http://example.org/foo")
    pb.add_constraint("http://example.org/record/Derived")

    result = list(helper.combine_property_lists([pa], [pb]))
    result2 = list(helper.combine_property_lists([pb], [pa]))

    assert list(result[0].range)[0] == derived
    assert list(result2[0].range)[0] == derived


def test_combine_property_lists_throws_when_literal_ranges_are_not_comparable():
    schema = Schema()
    helper = PropertyHelper(schema)
    pa = LiteralProperty("foo", "http://example.org/foo")
    rdf_lang_string = "http://www.w3.org/1999/02/22-rdf-syntax-ns#langString"
    pa.add_constraint(rdf_lang_string, min_inclusive="A")
    pb = LiteralProperty("foo", "http://example.org/foo")
    pb.add_constraint(rdf_lang_string, min_inclusive="a")
    with pytest.raises(NoComparatorException):
        list(helper.combine_property_lists([pa], [pb]))