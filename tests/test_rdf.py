"""Port of the Kotlin ``RdfParserTests`` and ``RdfBuilderTests``."""

from __future__ import annotations

import io

import pytest
from helpers import (
    assert_rdf_isomorphic,
    load_rdf,
    load_yaml,
    normalize,
    resource_path,
)
from rdflib import Graph

from record_spec.model import SchemaBuilder
from record_spec.rdf import RdfBuilder, RdfParser, RdfSerializer
from record_spec.serde import SchemaDefBuilder
from record_spec.yaml_parser import YamlParser

PARSE_CASES = ["simple", "literalProperties", "recordProperties", "inheritance", "mixins", "propertyMaps"]


@pytest.mark.parametrize("test_resource_name", PARSE_CASES)
def test_parse_rdf(test_resource_name: str):
    input_path = resource_path(f"rdf/{test_resource_name}.ttl")
    expected = load_yaml(f"rdf/{test_resource_name}.yaml")
    rdf_parser = RdfParser()
    with open(input_path, "rb") as input_stream:
        schema_adapter = rdf_parser.parse(input_stream, f"http://example.org/spec/{test_resource_name}.ttl")
    schema_def = SchemaDefBuilder().build(schema_adapter)
    actual = schema_def.to_dict()
    assert normalize(actual) == normalize(expected), (
        f"Parsed schema does not match rdf/{test_resource_name}.yaml.\n"
        f"actual: {actual}\nexpected: {expected}"
    )


def test_parse_simple():
    input_path = resource_path("rdf/simple.ttl")
    rdf_parser = RdfParser()
    with open(input_path, "rb") as input_stream:
        schema_adapter = rdf_parser.parse(input_stream, "http://example.org/spec/simple.ttl")
    model = SchemaBuilder().build(schema_adapter, input_path.as_uri(), validate=False)
    assert len(list(model.records)) == 1


def test_parse_throws_when_no_schema_in_model():
    rdf_parser = RdfParser()
    empty = b"@prefix ex: <http://example.org/> .\nex:a ex:b ex:c ."
    from record_spec.exceptions import RdfParserException

    with pytest.raises(RdfParserException):
        rdf_parser.parse(empty, "http://example.org/spec/none.ttl")


def test_parse_throws_when_multiple_schemas_in_model():
    rdf_parser = RdfParser()
    ttl = (
        b"@prefix rec: <http://vocab.epimorphics.com/record-spec/def/> .\n"
        b"@prefix s1: <http://example.org/s1/> .\n"
        b"@prefix s2: <http://example.org/s2/> .\n"
        b"s1:schema a rec:Schema .\n"
        b"s2:schema a rec:Schema .\n"
    )
    from record_spec.exceptions import RdfParserException

    with pytest.raises(RdfParserException):
        rdf_parser.parse(ttl, "http://example.org/spec/multi.ttl")


def test_parse_with_resource_uri_selects_schema():
    rdf_parser = RdfParser()
    ttl = (
        b"@prefix rec: <http://vocab.epimorphics.com/record-spec/def/> .\n"
        b"@prefix s1: <http://example.org/s1/> .\n"
        b"@prefix s2: <http://example.org/s2/> .\n"
        b"s1:schema a rec:Schema .\n"
        b"s2:schema a rec:Schema .\n"
    )
    schema_adapter = rdf_parser.parse(ttl, "http://example.org/spec/multi.ttl", resource_uri="http://example.org/s1/schema")
    assert schema_adapter.base_uri == "http://example.org/spec/multi.ttl"


def test_parse_with_unknown_resource_uri_throws():
    rdf_parser = RdfParser()
    ttl = (
        b"@prefix rec: <http://vocab.epimorphics.com/record-spec/def/> .\n"
        b"@prefix s1: <http://example.org/s1/> .\n"
        b"s1:schema a rec:Schema .\n"
    )
    from record_spec.exceptions import RdfParserException

    with pytest.raises(RdfParserException):
        rdf_parser.parse(ttl, "http://example.org/spec/x.ttl", resource_uri="http://example.org/other/schema")


@pytest.mark.parametrize("test_resource_name", PARSE_CASES)
def test_build_rdf_model(test_resource_name: str):
    input_path = resource_path(f"rdf/{test_resource_name}.yaml")
    expected_graph = load_rdf(f"rdf/{test_resource_name}_out.ttl")

    actual_graph = Graph()
    # Bind the same prefixes as the expected model so that any failure
    # diagnostics serialize comparably (isomorphism ignores prefixes).
    for prefix, namespace in expected_graph.namespaces():
        actual_graph.bind(prefix, namespace)

    with open(input_path) as f:
        schema_adapter = YamlParser().parse(f)
    RdfBuilder(actual_graph, "http://example.org/spec/schema").build(schema_adapter)

    assert_rdf_isomorphic(expected_graph, actual_graph)


def test_rdf_serializer_round_trips_builder_output():
    """RdfSerializer wraps RdfBuilder and writes a Turtle serialization."""
    with open(resource_path("rdf/simple.yaml")) as f:
        schema_adapter = YamlParser().parse(f)
    writer = io.StringIO()
    RdfSerializer().write(writer, schema_adapter)
    serialized = writer.getvalue()
    # rdflib binds prefixes itself; assert on the record-spec vocabulary
    # namespace being declared (the schema class URI is a prefixed name).
    assert "<http://vocab.epimorphics.com/record-spec/def/>" in serialized

    reparsed = RdfParser().parse(serialized, "http://example.org/spec/simple.ttl")
    schema = SchemaBuilder().build(reparsed, None, validate=False)
    assert len(list(schema.records)) == 1


def test_yaml_to_rdf_to_yaml_round_trip():
    """A YAML schema parsed to RDF and back yields the same def-tree (modulo prefix renaming)."""
    with open(resource_path("rdf/simple.yaml")) as f:
        schema_adapter = YamlParser().parse(f)

    graph = Graph()
    RdfBuilder(graph, "http://example.org/spec/schema").build(schema_adapter)
    serialized = graph.serialize(format="turtle")

    reparsed = RdfParser().parse(serialized, "http://example.org/spec/simple.ttl")
    schema_def = SchemaDefBuilder().build(reparsed)
    actual = schema_def.to_dict()
    expected = load_yaml("rdf/simple.yaml")
    assert normalize(actual) == normalize(expected)