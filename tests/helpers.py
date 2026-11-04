"""Shared test helpers (the Python equivalent of the Kotlin ``TestBase``)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

from record_spec.model import Schema, SchemaBuilder
from record_spec.serde import SchemaDefBuilder
from record_spec.yaml_parser import YamlParser

if TYPE_CHECKING:
    from rdflib import Graph

RESOURCES = Path(__file__).parent / "resources"


def load_yaml(resource: str) -> dict:
    with open(RESOURCES / resource.lstrip("/")) as f:
        return yaml.safe_load(f)


def load_json(resource: str) -> dict:
    with open(RESOURCES / resource.lstrip("/")) as f:
        return json.load(f)


def load_schema(resource: str, *, validate: bool = False) -> Schema:
    """Load a schema from a test resource, with the resource URI as the source URI."""
    with open(RESOURCES / resource.lstrip("/")) as f:
        schema_def = YamlParser().parse(f)
    source_uri = (RESOURCES / resource.lstrip("/")).as_uri()
    return SchemaBuilder().build(schema_def, source_uri, validate)


def schema_to_tree(schema: Schema) -> dict:
    """Serialize a schema to its def-tree dict (the Kotlin ``schemaToTree``)."""
    return SchemaDefBuilder().build(schema.adapter).to_dict()


def normalize(value):
    """Canonicalize a value for comparison: recursively sort lists (IGNORING_ARRAY_ORDER)."""
    if isinstance(value, dict):
        return {k: normalize(v) for k, v in value.items()}
    if isinstance(value, list):
        return sorted(json.dumps(normalize(item), sort_keys=True) for item in value)
    return value


def assert_yaml_serialisation(expected_resource: str, schema: Schema) -> None:
    """Assert that the schema serializes to the expected YAML resource."""
    expected = load_yaml(expected_resource)
    actual = schema_to_tree(schema)
    assert normalize(actual) == normalize(expected), (
        f"Schema serialization does not match {expected_resource}.\n"
        f"actual: {json.dumps(actual, indent=2, sort_keys=True)}\n"
        f"expected: {json.dumps(expected, indent=2, sort_keys=True)}"
    )


def resource_path(resource: str) -> Path:
    return RESOURCES / resource.lstrip("/")


def resource_uri(resource: str) -> str:
    return (RESOURCES / resource.lstrip("/")).as_uri()


def load_rdf(resource: str, format: str = "turtle") -> Graph:
    """Load an RDF test resource into a graph."""
    from rdflib import Graph

    graph = Graph()
    graph.parse(resource_path(resource), format=format)
    return graph


def normalize_string_literals(graph: Graph) -> Graph:
    """Return a copy of the graph in which ``xsd:string``-typed literals are
    replaced by plain literals.

    RDF 1.1 defines simple literals as identical to ``xsd:string``-typed
    literals, but rdflib's graph comparison (isomorphism / graph_diff)
    distinguishes them. Serializers differ in which form they emit
    (Jena emits plain literals), so both sides are normalized before
    comparing.
    """
    from rdflib import Graph as RdfLibGraph
    from rdflib.namespace import XSD
    from rdflib.term import Literal

    normalized = RdfLibGraph()
    for s, p, o in graph:
        if isinstance(o, Literal) and o.datatype == XSD.string:
            o = Literal(str(o))
        normalized.add((s, p, o))
    return normalized


def assert_rdf_isomorphic(expected: Graph, actual: Graph) -> None:
    """Assert that two RDF graphs are isomorphic (semantic comparison).

    On failure, prints a triple-level diff: triples present in the expected
    result but not the actual result, and vice versa (computed over
    canonicalized graphs so that blank nodes are comparable), followed by
    both graphs serialized as Turtle for context.
    """
    from rdflib.compare import graph_diff, isomorphic

    if isomorphic(expected, actual):
        return

    # graph_diff canonicalizes both graphs (blank nodes get stable labels)
    # so the reported differences are meaningful.
    _, in_expected, in_actual = graph_diff(expected, actual)
    missing = sorted(in_expected)
    extra = sorted(in_actual)

    message = "The generated RDF is not isomorphic with the expected RDF.\n"
    message += "\nTriples in the EXPECTED result but NOT in the actual result:\n"
    if not missing:
        message += "  (none — differences involve blank node structure only)\n"
    for triple in missing:
        message += f"  - {triple}\n"
    message += "\nTriples in the ACTUAL result but NOT in the expected result:\n"
    if not extra:
        message += "  (none — differences involve blank node structure only)\n"
    for triple in extra:
        message += f"  - {triple}\n"
    message += "\nActual:\n" + actual.serialize(format="turtle")
    message += "\nExpected:\n" + expected.serialize(format="turtle")
    raise AssertionError(message)


class TestListener:
    """The Python equivalent of the Kotlin ``TestListener``."""

    # Not a test class, despite the name.
    __test__ = False

    def __init__(self) -> None:
        self.received: list = []

    def on_event(self, event) -> None:
        self.received.append(event)

def load_schema_def(resource: str):
    """Load the raw SchemaDef from a test resource (no model built)."""
    from record_spec.serde import SchemaDef

    return SchemaDef.from_dict(load_yaml(resource))
