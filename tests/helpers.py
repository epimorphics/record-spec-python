"""Shared test helpers (the Python equivalent of the Kotlin ``TestBase``)."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from record_spec.model import Schema, SchemaBuilder
from record_spec.serde import SchemaDefBuilder
from record_spec.yaml_parser import YamlParser

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
