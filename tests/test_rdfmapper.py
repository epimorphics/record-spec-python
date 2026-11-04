"""Port of the Kotlin ``RdfMapperBuilderTests``."""

from __future__ import annotations

import pytest
from helpers import load_yaml, normalize, resource_path

from record_spec.model import SchemaBuilder
from record_spec.rdfmapper import RdfMapperBuilder, RdfMapperOptions
from record_spec.yaml_parser import YamlParser


def _build_model_from_resource(resource_path_str: str):
    path = resource_path(resource_path_str)
    with open(path) as f:
        schema_def = YamlParser().parse(f)
    return SchemaBuilder().build(schema_def, path.as_uri(), False)


MAPPER_CASES = [
    ("literals", "RecordA"),
    ("references", "RecordA"),
    ("references", "RecordB"),
    ("nested", "RecordA"),
    ("nested", "Recursive"),
    ("nested", "Circular"),
    ("nested", "Inheritance"),
    ("inheritance", "RecordA"),
]


@pytest.mark.parametrize(("test_resource_name", "test_record_name"), MAPPER_CASES)
def test_rdf_mapper_builder(test_resource_name, test_record_name):
    model_resource = f"rdfmapper/{test_resource_name}_model.yaml"
    expected_yaml = load_yaml(f"rdfmapper/{test_resource_name}_{test_record_name}.yaml")

    model = _build_model_from_resource(model_resource)
    record = model.resolve_record(test_record_name)
    builder = RdfMapperBuilder(RdfMapperOptions())
    actual_mapping_model = builder.build(model, record)
    actual_yaml = actual_mapping_model.to_dict()
    assert normalize(actual_yaml) == normalize(expected_yaml), (
        f"Generated rdf-mapper template does not match "
        f"rdfmapper/{test_resource_name}_{test_record_name}.yaml.\n"
        f"actual: {actual_yaml}\nexpected: {expected_yaml}"
    )


@pytest.mark.parametrize(("graph_add", "graph_pattern"), [(True, "<{@id}/graph>"), (False, "<{@id}/graph>")])
def test_graph_targeting_options(graph_add, graph_pattern):
    graph_prop = "graphAdd" if graph_add else "graph"
    model_resource = "rdfmapper/literals_model.yaml"
    expected_yaml = load_yaml(f"rdfmapper/literals_RecordA_{graph_prop}.yaml")

    model = _build_model_from_resource(model_resource)
    record = model.resolve_record("RecordA")
    builder = RdfMapperBuilder(RdfMapperOptions(graph_add=graph_add, graph_pattern=graph_pattern))
    actual_mapping_model = builder.build(model, record)
    actual_yaml = actual_mapping_model.to_dict()
    assert normalize(actual_yaml) == normalize(expected_yaml), (
        f"Generated rdf-mapper template does not match rdfmapper/literals_RecordA_{graph_prop}.yaml.\n"
        f"actual: {actual_yaml}\nexpected: {expected_yaml}"
    )