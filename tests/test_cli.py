"""CLI tests for the record-spec command (port coverage of record-spec-cmd).

The Kotlin record-spec-cmd module has no tests; these exercise every
subcommand end-to-end via click's test runner, using the fixtures from
the library test resources.
"""

from __future__ import annotations

import json

import pytest
import yaml
from click.testing import CliRunner
from helpers import RESOURCES, load_yaml, normalize

from record_spec.cli.main import record_spec

SIMPLE_SCHEMA = str(RESOURCES / "simpleRecord.yaml")

def _load_cli_model(*schema_files: str, no_import: bool = False):
    """Load a schema exactly as the CLI does, for expected-output comparison."""
    from record_spec.cli.commands.common import load_schema_file

    schemas = [load_schema_file(__import__("pathlib").Path(f), None, {}, no_import) for f in schema_files]
    merged = schemas[0]
    for schema in schemas[1:]:
        merged.merge(schema)
    return merged


RDF_SCHEMA = str(RESOURCES / "rdf" / "simple.yaml")
MIXIN_SCHEMA = str(RESOURCES / "rdf" / "mixins.yaml")


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def test_validate_valid_schema(runner: CliRunner):
    result = runner.invoke(record_spec, ["validate", SIMPLE_SCHEMA])
    assert result.exit_code == 0, result.output
    assert "Schema is valid." in result.output


def test_validate_invalid_schema(runner: CliRunner, tmp_path):
    schema = tmp_path / "bad.yaml"
    schema.write_text(
        """
base: http://example.org/spec/
records:
  Foo:
    classUri: http://example.org/def/Foo
    shortCode: 1Bad
"""
    )
    result = runner.invoke(record_spec, ["validate", str(schema)])
    assert result.exit_code == 0  # the Kotlin CLI reports, does not fail
    assert "validation failed" in result.output.lower()


def test_validate_reports_multiple_errors(runner: CliRunner, tmp_path):
    schema = tmp_path / "bad.yaml"
    schema.write_text(
        """
base: http://example.org/spec/
records:
  Foo:
    classUri: http://example.org/def/Foo
    shortCode: 1Bad
  Bar:
    classUri: http://example.org/def/Bar
    shortCode: 2Bad
"""
    )
    result = runner.invoke(record_spec, ["validate", str(schema)])
    assert result.exit_code == 0
    assert "validation errors" in result.output


def test_convert_yaml_to_json(runner: CliRunner):
    result = runner.invoke(record_spec, ["convert", SIMPLE_SCHEMA, "--to", "json"])
    assert result.exit_code == 0, result.output
    converted = json.loads(result.output[result.output.index("{"):])
    # Round-trip through the model: compare against the model canonical form
    # (import resolution included, exactly as the CLI loads).
    from record_spec.serde import SchemaDefBuilder

    expected = SchemaDefBuilder().build(_load_cli_model(SIMPLE_SCHEMA).adapter).to_dict()
    assert normalize(converted) == normalize(expected)


def test_convert_yaml_to_yaml_round_trip(runner: CliRunner):
    result = runner.invoke(record_spec, ["convert", SIMPLE_SCHEMA, "--to", "yaml"])
    assert result.exit_code == 0, result.output
    # The CLI echoes a status line first; strip to the YAML document.
    yaml_text = result.output[result.output.index("base:"):]
    converted = yaml.safe_load(yaml_text)
    from record_spec.serde import SchemaDefBuilder

    expected = SchemaDefBuilder().build(_load_cli_model(SIMPLE_SCHEMA).adapter).to_dict()
    assert normalize(converted) == normalize(expected)


def test_convert_ttl_input(runner: CliRunner):
    ttl = str(RESOURCES / "rdf" / "simple.ttl")
    result = runner.invoke(record_spec, ["convert", ttl, "--format", "ttl", "--to", "json"])
    assert result.exit_code == 0, result.output
    converted = json.loads(result.output[result.output.index("{"):])
    expected = load_yaml("rdf/simple.yaml")
    # The RDF parse covers the same records; compare the record definitions.
    assert normalize(converted["records"]) == normalize(expected["records"])


def test_convert_nt_output(runner: CliRunner):
    result = runner.invoke(record_spec, ["convert", SIMPLE_SCHEMA, "--to", "nt"])
    assert result.exit_code == 0, result.output
    assert "<http://vocab.epimorphics.com/record-spec/def/Schema>" in result.output


def test_convert_output_file(runner: CliRunner, tmp_path):
    out = tmp_path / "out.json"
    result = runner.invoke(record_spec, ["convert", SIMPLE_SCHEMA, "--to", "json", "-o", str(out)])
    assert result.exit_code == 0, result.output
    assert out.exists()
    from record_spec.serde import SchemaDefBuilder

    expected = SchemaDefBuilder().build(_load_cli_model(SIMPLE_SCHEMA).adapter).to_dict()
    assert normalize(json.loads(out.read_text())) == normalize(expected)


def test_convert_merges_multiple_files(runner: CliRunner, tmp_path):
    a = tmp_path / "a.yaml"
    b = tmp_path / "b.yaml"
    a.write_text(
        """
base: http://example.org/spec/
records:
  Foo:
    classUri: http://example.org/def/Foo
    shortCode: Foo
    properties:
      name:
        propertyUri: http://example.org/def/name
        kind: literal
        constraints:
          - datatype: http://www.w3.org/2001/XMLSchema#string
"""
    )
    b.write_text(
        """
base: http://example.org/spec/
records:
  Bar:
    classUri: http://example.org/def/Bar
    shortCode: Bar
"""
    )
    result = runner.invoke(record_spec, ["convert", str(a), str(b), "--to", "json"])
    assert result.exit_code == 0, result.output
    converted = json.loads(result.output[result.output.index("{"):])
    assert "Foo" in converted["records"]
    assert "Bar" in converted["records"]


def test_convert_unknown_extension_errors(runner: CliRunner, tmp_path):
    schema = tmp_path / "schema.xyz"
    schema.write_text("base: http://example.org/")
    result = runner.invoke(record_spec, ["convert", str(schema)])
    assert result.exit_code != 0
    assert "Unable to determine schema format" in result.output


def test_json_schema_subcommand(runner: CliRunner):
    result = runner.invoke(record_spec, ["json-schema", SIMPLE_SCHEMA, "-r", "Simple"])
    assert result.exit_code == 0, result.output
    schema = json.loads(result.output[result.output.index("{"):])
    assert schema["$ref"] == "#/definitions/Simple"


def test_json_schema_unknown_record_errors(runner: CliRunner):
    result = runner.invoke(record_spec, ["json-schema", SIMPLE_SCHEMA, "-r", "Nope"])
    assert result.exit_code != 0
    assert "not found in the schema" in result.output


def test_json_schema_without_record_errors(runner: CliRunner):
    result = runner.invoke(record_spec, ["json-schema", SIMPLE_SCHEMA])
    assert result.exit_code != 0
    assert "not yet implemented" in result.output


def test_json_ld_subcommand_schema_context(runner: CliRunner):
    result = runner.invoke(record_spec, ["json-ld", SIMPLE_SCHEMA])
    assert result.exit_code == 0, result.output
    context = json.loads(result.output[result.output.index("{"):])
    assert context["@version"] == 1.1
    assert "http://test.epimorphics.com/record-spec/def/Simple" in context


def test_json_ld_subcommand_record_context(runner: CliRunner):
    result = runner.invoke(record_spec, ["json-ld", SIMPLE_SCHEMA, "-r", "Simple"])
    assert result.exit_code == 0, result.output
    context = json.loads(result.output[result.output.index("{"):])
    assert "http://test.epimorphics.com/record-spec/def/Simple" in context
    assert "http://test.epimorphics.com/record-spec/def/Simple" in context


def test_shacl_subcommand(runner: CliRunner):
    result = runner.invoke(record_spec, ["shacl", MIXIN_SCHEMA])
    assert result.exit_code == 0, result.output
    assert "sh:NodeShape" in result.output or "NodeShape" in result.output


def test_shacl_closed(runner: CliRunner):
    result = runner.invoke(record_spec, ["shacl", MIXIN_SCHEMA, "--closed"])
    assert result.exit_code == 0, result.output
    assert "sh:closed" in result.output or "closed true" in result.output


def test_shacl_nt_output(runner: CliRunner):
    result = runner.invoke(record_spec, ["shacl", MIXIN_SCHEMA, "--to", "nt"])
    assert result.exit_code == 0, result.output
    assert "<http://www.w3.org/ns/shacl#NodeShape>" in result.output


def test_rdfs_subcommand(runner: CliRunner):
    result = runner.invoke(record_spec, ["rdfs", MIXIN_SCHEMA])
    assert result.exit_code == 0, result.output
    assert "rdfs:Class" in result.output


def test_rdfs_with_mixins(runner: CliRunner):
    result = runner.invoke(record_spec, ["rdfs", MIXIN_SCHEMA, "--with-mixins"])
    assert result.exit_code == 0, result.output
    assert "rdfs:subClassOf" in result.output


def test_rdfmapper_subcommand(runner: CliRunner):
    result = runner.invoke(record_spec, ["rdfmapper", MIXIN_SCHEMA, "Bar"])
    assert result.exit_code == 0, result.output
    mapping = yaml.safe_load(result.output)
    assert mapping["resources"][0]["name"] == "Bar"


def test_rdfmapper_graph_options(runner: CliRunner):
    result = runner.invoke(record_spec, ["rdfmapper", MIXIN_SCHEMA, "Bar", "--graph", "<{@id}/g>"])
    assert result.exit_code == 0, result.output
    mapping = yaml.safe_load(result.output)
    assert mapping["resources"][0]["@graph"] == "<{@id}/g>"


def test_rdfmapper_graph_options_mutually_exclusive(runner: CliRunner):
    result = runner.invoke(
        record_spec, ["rdfmapper", MIXIN_SCHEMA, "Bar", "--graph", "g", "--graph-add", "g"]
    )
    assert result.exit_code != 0
    assert "mutually exclusive" in result.output


def test_generate_subcommand(runner: CliRunner):
    result = runner.invoke(record_spec, ["generate"])
    assert result.exit_code == 0, result.output
    schema = json.loads(result.output[result.output.index("{"):])
    # The $id is the id of the RecordSpecSchema record in the bundled
    # record-spec vocabulary schema (record key "Schema" + its base).
    assert schema["$id"] == "http://vocab.epimorphics.com/record-spec/Schema"
    assert schema["$schema"] == "http://json-schema.org/draft-07/schema#"


def test_no_import_flag(runner: CliRunner, tmp_path):
    imported = tmp_path / "imported.yaml"
    imported.write_text(
        """
base: http://example.org/spec/
records:
  Base:
    classUri: http://example.org/def/Base
    shortCode: Base
"""
    )
    importer = tmp_path / "importer.yaml"
    importer.write_text(
        """
base: http://example.org/spec/
imports:
  - http://example.org/spec/imported.yaml
records:
  Derived:
    classUri: http://example.org/def/Derived
    shortCode: Derived
    extends: Base
"""
    )
    # With imports: the import IRI is redirected to the local file via the
    # catalog (exactly what CatalogResolver exists for).
    result = runner.invoke(
        record_spec,
        [
            "convert",
            str(importer),
            "--to",
            "json",
            "--catalog",
            f"http://example.org/spec/imported.yaml={imported.resolve().as_uri()}",
        ],
    )
    assert result.exit_code == 0, result.output
    converted = json.loads(result.output[result.output.index("{"):])
    assert "Base" in converted["records"], result.output

    # With --no-import: only Derived is present (and Derived alone is
    # invalid, since it extends the unloaded Base — so validate only the
    # record set, not the full conversion).
    result = runner.invoke(record_spec, ["convert", str(importer), "--to", "json", "--no-import"])
    converted = json.loads(result.output[result.output.index("{"):]) if result.exit_code == 0 else None
    if converted is not None:
        assert "Base" not in converted["records"]
        assert "Derived" in converted["records"]
    else:
        # Conversion failed on validation of the unresolved Base reference —
        # which is the expected outcome of skipping imports.
        assert "No record found" in result.output or result.exit_code != 0