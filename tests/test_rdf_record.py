"""Port of the Kotlin ``RdfRecordTests``: RDF instance ⇄ JSON tree."""

from __future__ import annotations

import pytest
from helpers import (
    assert_rdf_isomorphic,
    load_json,
    load_rdf,
    normalize,
    resource_path,
)
from rdflib import Graph, Literal, URIRef

from record_spec.jsonschema import JsonOptions
from record_spec.model import SchemaBuilder
from record_spec.rdf import RdfRecordReader, RdfRecordWriter
from record_spec.yaml_parser import YamlParser

RECORD_CASES = [
    ("stringProp", "http://example.org/test", "Foo"),
    ("langStringProp", "http://example.org/test", "Foo"),
    ("floatProp", "http://example.org/test", "Foo"),
    ("doubleProp", "http://example.org/test", "Foo"),
    ("decimalProp", "http://example.org/test", "Foo"),
    ("booleanProp", "http://example.org/test", "Foo"),
    ("reference", "http://example.org/test", "Bar"),
    ("nest", "http://example.org/test", "Bar"),
]


def _load_schema():
    with open(resource_path("rdf-records/schema.yaml")) as f:
        return SchemaBuilder().build(YamlParser().parse(f), None, True)


@pytest.mark.parametrize(("test_name", "resource_uri", "record_def"), RECORD_CASES)
def test_rdf_to_json(test_name, resource_uri, record_def):
    model = load_rdf(f"rdf-records/{test_name}.ttl")
    expected_json = load_json(f"rdf-records/{test_name}.json")
    reader = RdfRecordReader(model, _load_schema())
    actual_json = reader.read_value(URIRef(resource_uri), _load_schema().resolve_record(record_def))
    assert normalize(actual_json) == normalize(expected_json), (
        f"Read record does not match rdf-records/{test_name}.json.\n"
        f"actual: {actual_json}\nexpected: {expected_json}"
    )


@pytest.mark.parametrize(("test_name", "resource_uri", "record_def"), RECORD_CASES)
def test_json_to_rdf(test_name, resource_uri, record_def):
    expected_model = load_rdf(f"rdf-records/{test_name}.ttl")
    actual_model = Graph()
    json_tree = load_json(f"rdf-records/{test_name}.json")
    writer = RdfRecordWriter(actual_model, JsonOptions())
    writer.write_record(json_tree, _load_schema().resolve_record(record_def))
    assert_rdf_isomorphic(expected_model, actual_model)


# ---- reader/writer error and edge cases (mirroring the Kotlin raises) ----


def _make_schema():
    """A schema with required, repeatable and nested property variants."""
    from record_spec.model import Schema
    from record_spec.values import XSD

    schema = Schema()
    schema.set_base("http://example.org/record/")
    foo = schema.create_record("http://example.org/record/Foo", "http://example.org/def/Foo", "Foo")
    foo.create_literal_property(
        "stringProp", "http://example.org/def/stringProp", required=True
    ).add_constraint(XSD + "string")
    foo.create_literal_property("notes", "http://example.org/def/notes", repeatable=True).add_constraint(XSD + "string")
    bar = schema.create_record("http://example.org/record/Bar", "http://example.org/def/Bar", "Bar")
    bar.create_record_property(
        "nestedFoo", "http://example.org/def/nestedFoo", nested=True
    ).add_constraint("http://example.org/record/Foo")
    bar.create_record_property("refFoo", "http://example.org/def/refFoo").add_constraint("http://example.org/record/Foo")
    schema.validate()
    return schema


def test_reader_throws_on_missing_required_property():
    from record_spec.exceptions import RdfRecordReaderException

    schema = _make_schema()
    model = Graph()
    reader = RdfRecordReader(model, schema)
    with pytest.raises(RdfRecordReaderException):
        reader.read_value(URIRef("http://example.org/test"), schema.resolve_record("Foo"))


def test_reader_throws_on_multiple_values_for_non_repeatable():
    from record_spec.exceptions import RdfRecordReaderException

    schema = _make_schema()
    model = Graph()
    model.add((URIRef("http://example.org/test"), URIRef("http://example.org/def/stringProp"), Literal("one")))
    model.add((URIRef("http://example.org/test"), URIRef("http://example.org/def/stringProp"), Literal("two")))
    reader = RdfRecordReader(model, schema)
    with pytest.raises(RdfRecordReaderException):
        reader.read_value(URIRef("http://example.org/test"), schema.resolve_record("Foo"))


def test_reader_throws_on_untyped_nested_resource():
    from record_spec.exceptions import RdfRecordReaderException

    schema = _make_schema()
    model = Graph()
    # A nested resource with no rdf:type and a property whose constraint
    # does not match: the type cannot be inferred.
    model.add(
        (URIRef("http://example.org/test"), URIRef("http://example.org/def/nestedFoo"), URIRef("http://example.org/foo"))
    )
    reader = RdfRecordReader(model, schema)
    with pytest.raises(RdfRecordReaderException):
        reader.read_value(URIRef("http://example.org/test"), schema.resolve_record("Bar"))


def test_reader_reads_repeatable_property_as_array():
    schema = _make_schema()
    model = Graph()
    model.add((URIRef("http://example.org/test"), URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"), URIRef("http://example.org/def/Foo")))
    model.add((URIRef("http://example.org/test"), URIRef("http://example.org/def/stringProp"), Literal("main")))
    model.add((URIRef("http://example.org/test"), URIRef("http://example.org/def/notes"), Literal("a")))
    model.add((URIRef("http://example.org/test"), URIRef("http://example.org/def/notes"), Literal("b")))
    reader = RdfRecordReader(model, schema)
    actual = reader.read_value(URIRef("http://example.org/test"), schema.resolve_record("Foo"))
    assert actual["notes"] == ["a", "b"]
    assert actual["stringProp"] == "main"


def test_writer_throws_on_null_required_property():
    from record_spec.exceptions import RdfRecordWriterException

    schema = _make_schema()
    model = Graph()
    writer = RdfRecordWriter(model, JsonOptions())
    tree = {"@id": "http://example.org/test", "stringProp": None}
    with pytest.raises(RdfRecordWriterException):
        writer.write_record(tree, schema.resolve_record("Foo"))


def test_writer_skips_null_optional_property():
    schema = _make_schema()
    model = Graph()
    writer = RdfRecordWriter(model, JsonOptions())
    tree = {"@id": "http://example.org/test", "notes": None}
    writer.write_record(tree, schema.resolve_record("Foo"))
    assert len(model) == 1  # only the rdf:type triple


def test_writer_wraps_repeatable_arrays():
    schema = _make_schema()
    model = Graph()
    writer = RdfRecordWriter(model, JsonOptions())
    tree = {
        "@id": "http://example.org/test",
        "stringProp": "main",
        "notes": ["one", "two"],
    }
    writer.write_record(tree, schema.resolve_record("Foo"))
    values = sorted(str(o) for _, _, o in model.triples((None, URIRef("http://example.org/def/notes"), None)))
    assert values == ["one", "two"]


def test_writer_writes_bnode_without_id():
    schema = _make_schema()
    model = Graph()
    writer = RdfRecordWriter(model, JsonOptions())
    tree = {"stringProp": "anon"}
    resource = writer.write_record(tree, schema.resolve_record("Foo"))
    assert isinstance(resource, URIRef) or resource.__class__.__name__ == "BNode"