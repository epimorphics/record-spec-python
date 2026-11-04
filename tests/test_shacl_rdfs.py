"""Ports of the Kotlin ``ShaclBuilderTests`` and ``RdfsBuilderTests``."""

from __future__ import annotations

import pytest
from helpers import assert_rdf_isomorphic, load_rdf, resource_path
from rdflib import Graph

from record_spec.model import SchemaBuilder
from record_spec.rdf import RdfsBuilder, RdfsOptions, ShaclBuilder, ShaclOptions
from record_spec.yaml_parser import YamlParser


def _load_schema(resource: str):
    with open(resource_path(resource)) as f:
        return SchemaBuilder().build(YamlParser().parse(f), None, True)


def _bind_prefixes(actual: Graph, expected: Graph) -> None:
    for prefix, namespace in expected.namespaces():
        actual.bind(prefix, namespace)


SHACL_CASES = ["simple", "mixins", "inheritance", "literalProperties", "recordProperties", "propertyMaps"]


@pytest.mark.parametrize("test_resource_name", SHACL_CASES)
def test_build_shacl_model(test_resource_name):
    expected_model = load_rdf(f"rdf/{test_resource_name}_shacl.ttl")
    schema = _load_schema(f"rdf/{test_resource_name}.yaml")

    actual_model = Graph()
    _bind_prefixes(actual_model, expected_model)
    ShaclBuilder(actual_model, ShaclOptions()).build(schema)

    assert_rdf_isomorphic(expected_model, actual_model)


@pytest.mark.parametrize("test_resource_name", ["inheritance", "propertyMaps"])
def test_build_closed_model(test_resource_name):
    expected_model = load_rdf(f"rdf/{test_resource_name}_shacl_closed.ttl")
    schema = _load_schema(f"rdf/{test_resource_name}.yaml")

    actual_model = Graph()
    _bind_prefixes(actual_model, expected_model)
    ShaclBuilder(actual_model, ShaclOptions(closed=True)).build(schema)

    assert_rdf_isomorphic(expected_model, actual_model)


@pytest.mark.parametrize(("test_resource_name", "ignore_record"), [("propertyMaps", "Foo")])
def test_build_model_with_ignored_record(test_resource_name, ignore_record):
    expected_model = load_rdf(f"rdf/{test_resource_name}_shacl_ex_{ignore_record}.ttl")
    schema = _load_schema(f"rdf/{test_resource_name}.yaml")

    actual_model = Graph()
    _bind_prefixes(actual_model, expected_model)
    ShaclBuilder(actual_model, ShaclOptions(exclude_records=[ignore_record])).build(schema)

    assert_rdf_isomorphic(expected_model, actual_model)


RDFS_CASES = ["simple", "mixins", "inheritance"]


@pytest.mark.parametrize("test_resource_name", RDFS_CASES)
def test_build_rdfs_model(test_resource_name):
    expected_model = load_rdf(f"rdf/{test_resource_name}_rdfs.ttl")
    schema = _load_schema(f"rdf/{test_resource_name}.yaml")

    actual_model = Graph()
    _bind_prefixes(actual_model, expected_model)
    RdfsBuilder(actual_model, RdfsOptions()).build(schema)

    assert_rdf_isomorphic(expected_model, actual_model)


def test_build_rdfs_model_with_mixins():
    test_resource_name = "mixins"
    expected_model = load_rdf(f"rdf/{test_resource_name}_rdfs_mixins.ttl")
    schema = _load_schema(f"rdf/{test_resource_name}.yaml")

    actual_model = Graph()
    _bind_prefixes(actual_model, expected_model)
    RdfsBuilder(actual_model, RdfsOptions(with_mixins=True)).build(schema)

    assert_rdf_isomorphic(expected_model, actual_model)