"""Ports of the Kotlin ``JsonLdContextBuilderTests`` and ``JsonLdContextEvaluationTests``."""

from __future__ import annotations

import json

import pytest
from helpers import (
    assert_rdf_isomorphic,
    load_json,
    load_rdf,
    normalize,
    normalize_string_literals,
    resource_path,
)
from rdflib import Graph

from record_spec.jsonschema import JsonLdContextBuilder, JsonOptions
from record_spec.model import SchemaBuilder
from record_spec.rdf import ShaclBuilder, ShaclOptions
from record_spec.yaml_parser import YamlParser

SCHEMA_CONTEXT_CASES = [
    ("simple", JsonOptions(), "context.json"),
    ("simple", JsonOptions(bare_reference_ids=True), "context.bareIds.json"),
    ("simple", JsonOptions(id_property="id", type_property="rdfType"), "context.customProps.json"),
    ("mixins", JsonOptions(), "context.json"),
    ("mappedProperties", JsonOptions(), "context.json"),
    ("arbitraryLiterals", JsonOptions(), "context.json"),
    ("inheritance", JsonOptions(), "context.json"),
    ("reversed", JsonOptions(), "context.json"),
]

RECORD_CONTEXT_CASES = [
    ("simple", "http://example.org/spec/Foo", JsonOptions(), "Foo.context.json"),
    ("simple", "http://example.org/spec/Bar", JsonOptions(), "Bar.context.json"),
    ("simple", "http://example.org/spec/Bar", JsonOptions(bare_reference_ids=True), "Bar.context.bareIds.json"),
    ("nested", "http://example.org/spec/Foo", JsonOptions(), "Foo.context.json"),
]


def _load_schema(test_name: str):
    with open(resource_path(f"json/{test_name}/schema.yaml")) as f:
        return SchemaBuilder().build(YamlParser().parse(f), None, True)


def _load_json_tree(test_name: str, resource_name: str) -> dict:
    return load_json(f"json/{test_name}/{resource_name}")


@pytest.mark.parametrize(("test_name", "options", "expected_resource_name"), SCHEMA_CONTEXT_CASES)
def test_schema_context_generation(test_name, options, expected_resource_name):
    schema = _load_schema(test_name)
    expected_json = _load_json_tree(test_name, expected_resource_name)
    actual_json = JsonLdContextBuilder(options).make_schema_context(schema)
    assert normalize(actual_json) == normalize(expected_json), (
        f"Generated JSON-LD context does not match json/{test_name}/{expected_resource_name}.\n"
        f"actual: {actual_json}\nexpected: {expected_json}"
    )


@pytest.mark.parametrize(("test_name", "record_id", "options", "expected_resource_name"), RECORD_CONTEXT_CASES)
def test_record_context_generation(test_name, record_id, options, expected_resource_name):
    schema = _load_schema(test_name)
    expected_json = _load_json_tree(test_name, expected_resource_name)
    actual_json = JsonLdContextBuilder(options).make_record_context(schema.resolve_record(record_id))
    assert normalize(actual_json) == normalize(expected_json), (
        f"Generated JSON-LD context does not match json/{test_name}/{expected_resource_name}.\n"
        f"actual: {actual_json}\nexpected: {expected_json}"
    )


EVALUATION_CASES = [
    ("simple", "http://example.org/spec/Foo", "record01.json", "record01.ttl", JsonOptions()),
    ("simple", "http://example.org/spec/Foo", "record02.json", "record02.ttl", JsonOptions(bare_reference_ids=True)),
    ("nested", "http://example.org/spec/Foo", "record01.json", "record01.ttl", JsonOptions()),
    ("mappedProperties", "http://example.org/spec/Foo", "record01.json", "record01.ttl", JsonOptions()),
    ("mappedProperties", "http://example.org/spec/Foo", "record02.json", "record02.ttl", JsonOptions()),
    ("jsonLiterals", "http://example.org/spec/Foo", "record01.json", "record01.ttl", JsonOptions()),
]


@pytest.mark.parametrize(
    ("test_name", "record_id", "json_resource_name", "expected_rdf_resource_name", "options"),
    EVALUATION_CASES,
)
def test_json_ld_context_evaluation(test_name, record_id, json_resource_name, expected_rdf_resource_name, options):
    """Expand a record JSON instance with the generated context and check the RDF."""
    schema = _load_schema(test_name)
    context = JsonLdContextBuilder(options).make_schema_context(schema.adapter)
    json_tree = _load_json_tree(test_name, json_resource_name)
    json_tree["@context"] = context

    expected_model = load_rdf(f"json/{test_name}/{expected_rdf_resource_name}")

    actual_model = Graph()
    actual_model.parse(data=json.dumps(json_tree), format="json-ld", publicID="")

    assert_rdf_isomorphic(normalize_string_literals(expected_model), normalize_string_literals(actual_model))

    # Generated RDF should be valid against the generated SHACL model
    shacl_model = Graph()
    ShaclBuilder(shacl_model, ShaclOptions()).build(schema)
    shapes_path = resource_path(f"json/{test_name}/shapes.ttl")
    if shapes_path.exists():
        expect_shacl_model = Graph()
        expect_shacl_model.parse(shapes_path, format="turtle")
        assert_rdf_isomorphic(expect_shacl_model, shacl_model)
    assert_validates(shacl_model, actual_model)


def assert_validates(shacl_model: Graph, data_model: Graph) -> None:
    """Assert that the data model validates against the shapes graph."""
    import pyshacl

    conforms, _, results_text = pyshacl.validate(data_model, shacl_graph=shacl_model)
    assert conforms, (
        "The generated RDF does not validate against the generated shapes graph for the model.\n"
        f"Validation report:\n{results_text}"
    )