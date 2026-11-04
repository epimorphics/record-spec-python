"""Port of the Kotlin ``ImportTests``."""

from __future__ import annotations

import pytest
from helpers import load_yaml, normalize, resource_path, schema_to_tree

from record_spec.model import SchemaBuilder
from record_spec.resolver import BasicSchemaResolver, CachingSchemaResolver, CatalogResolver
from record_spec.yaml_parser import YamlParser

IMPORT_CASES = ["simple", "mixed_schemas"]


@pytest.mark.parametrize("test_name", IMPORT_CASES)
def test_import(test_name: str):
    test_path = resource_path(f"import/{test_name}/test.yaml")
    expected_yaml = load_yaml(f"import/{test_name}/expected.yaml")

    # Load as the Kotlin TestBase does: no source URI, no validation.
    with open(test_path) as f:
        schema_def = YamlParser().parse(f)
    base_schema = SchemaBuilder().build(schema_def, None, validate=False)

    resolver = BasicSchemaResolver(test_path.as_uri())
    resolved_schema = base_schema.resolve_imports(resolver)
    actual_yaml = schema_to_tree(resolved_schema)
    assert normalize(actual_yaml) == normalize(expected_yaml), (
        f"Resolved schema does not match import/{test_name}/expected.yaml.\n"
        f"actual: {actual_yaml}\nexpected: {expected_yaml}"
    )


def test_import_removes_import_statements():
    test_path = resource_path("import/simple/test.yaml")
    with open(test_path) as f:
        schema_def = YamlParser().parse(f)
    base_schema = SchemaBuilder().build(schema_def, None, validate=False)
    assert len(list(base_schema.imports)) == 1

    resolver = BasicSchemaResolver(test_path.as_uri())
    resolved_schema = base_schema.resolve_imports(resolver)
    assert len(list(resolved_schema.imports)) == 0


def test_caching_resolver_returns_cached_schema():
    class CountingResolver:
        """A resolver that counts how many times it is called."""

        def __init__(self) -> None:
            self.calls = 0

        def resolve(self, uri: str):
            self.calls += 1
            with open(resource_path("import/simple/base.yaml")) as f:
                schema_def = YamlParser().parse(f)
            return SchemaBuilder().build(schema_def, None, validate=False)

    inner = CountingResolver()
    caching = CachingSchemaResolver(inner)
    first = caching.resolve("http://example.org/base.yaml")
    second = caching.resolve("http://example.org/base.yaml")
    assert inner.calls == 1
    assert first is second


def test_catalog_resolver_redirects():
    class StubResolver:
        def __init__(self) -> None:
            self.resolved: list[str] = []

        def resolve(self, uri: str):
            self.resolved.append(uri)
            with open(resource_path("import/simple/base.yaml")) as f:
                schema_def = YamlParser().parse(f)
            return SchemaBuilder().build(schema_def, None, validate=False)

    stub = StubResolver()
    catalog = CatalogResolver(
        {"http://example.org/requested": "http://example.org/actual"}, stub
    )
    catalog.resolve("http://example.org/requested")
    assert stub.resolved == ["http://example.org/actual"]
    catalog.resolve("http://example.org/direct")
    assert stub.resolved == ["http://example.org/actual", "http://example.org/direct"]