"""Shared command plumbing: schema loading, output writing.

The Python equivalent of the Kotlin ``SchemaCommand``, ``JsonCommand`` and
``SchemaWriter`` base classes.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import click
import yaml

from record_spec.jsonschema import JsonOptions
from record_spec.model import SchemaBuilder
from record_spec.rdf import RdfParser
from record_spec.resolver import BasicSchemaResolver, CatalogResolver
from record_spec.yaml_parser import JsonParser, YamlParser

if TYPE_CHECKING:

    from record_spec.model import Schema

#: The schema URI used when writing RDF without a schema id or output file.
DEFAULT_SCHEMA_URI = "http://vocab.epimorphics.com/record-spec/id/default-schema-id"

FORMAT_EXTENSIONS = {".json": "json", ".yaml": "yaml", ".yml": "yaml", ".ttl": "ttl", ".nt": "ttl"}


def guess_format_from_extension(schema_file: Path) -> str:
    """Determine the schema format from the file extension (the Kotlin
    ``guessFormFromFileExtension``)."""
    extension = schema_file.suffix.lower()
    if extension in FORMAT_EXTENSIONS:
        return FORMAT_EXTENSIONS[extension]
    raise click.UsageError(
        f"Unable to determine schema format for source file {schema_file.resolve()} "
        "(use --format to specify the format)"
    )


def load_schema_file(schema_file: Path, from_format: str | None, catalog: dict[str, str], no_import: bool) -> Schema:
    """Load a single schema file (the Kotlin ``loadSchemaFile``)."""
    from_format = from_format or guess_format_from_extension(schema_file)
    source_uri = schema_file.resolve().as_uri()
    with open(schema_file, "rb") as f:
        if from_format == "json":
            schema = SchemaBuilder().build(JsonParser().parse(f.read()), source_uri, validate=False)
        elif from_format == "yaml":
            schema = SchemaBuilder().build(YamlParser().parse(f), source_uri, validate=False)
        elif from_format == "ttl":
            schema = SchemaBuilder().build(RdfParser().parse(f, source_uri, "TTL"), source_uri, validate=False)
        else:  # pragma: no cover - guarded by the choice option
            raise click.UsageError(f"Unknown format {from_format}")
    if not no_import:
        resolved_catalog = catalog if isinstance(catalog, dict) else _collect_catalog(catalog)
        resolver = CatalogResolver(resolved_catalog, BasicSchemaResolver(source_uri))
        return schema.resolve_imports(resolver)
    return schema


class SchemaCommandMixin:
    """Provides schema loading to commands (the Kotlin ``SchemaCommand``)."""

    from_format: str | None
    schema_files: tuple[Path, ...]
    catalog: tuple[str, ...]
    no_import: bool

    def _load_schema(self) -> Schema:
        """Load all schema files and merge them into one schema."""
        catalog = _collect_catalog(self.catalog) if isinstance(self.catalog, tuple) else dict(self.catalog)
        schemas = [
            load_schema_file(schema_file, self.from_format, catalog, self.no_import)
            for schema_file in self.schema_files
        ]
        merged = schemas[0]
        for schema in schemas[1:]:
            merged.merge(schema)
        return merged


def schema_command_options(command: Any) -> Any:
    """Decorator applying the shared schema-loading options to a command."""
    options = [
        click.option(
            "-f",
            "--format",
            "from_format",
            type=click.Choice(["yaml", "json", "ttl"]),
            help="The format of the schema to be read.",
        ),
        click.option(
            "--catalog",
            multiple=True,
            help="A catalog mapping of a schema URI to the URL to use to locate the schema (URI=URL).",
        ),
        click.option("--no-import", is_flag=True, help="Do not process the imports of the schema."),
    ]
    for option in reversed(options):
        command = option(command)
    return command


class JsonCommandMixin(SchemaCommandMixin):
    """Provides JSON options to commands (the Kotlin ``JsonCommand``)."""

    with_bare_ids: bool
    type_tag: str
    value_tag: str
    language_tag: str
    optional_type: bool
    no_subclasses: bool
    no_additional_properties: bool
    allow_json_ld_context: bool
    allow_json_schema_ref: bool

    def _get_json_options(self) -> JsonOptions:
        return JsonOptions(
            bare_reference_ids=self.with_bare_ids,
            type_property=self.type_tag,
            value_property=self.value_tag,
            language_property=self.language_tag,
            optional_type_property=self.optional_type,
            with_subclasses=not self.no_subclasses,
            additional_properties=not self.no_additional_properties,
            allow_json_ld_context=self.allow_json_ld_context,
            allow_json_schema_ref=self.allow_json_schema_ref,
        )


def json_command_options(command: Any) -> Any:
    """Decorator applying the shared JSON options to a command."""
    options = [
    click.option(
        "--with-bare-ids",
        "with_bare_ids",
        is_flag=True,
        help="Whether to use bare strings for id references in JSON.",
    ),
    click.option("--type-tag", "type_tag", default="@type", show_default=True),
    click.option("--value-tag", "value_tag", default="@value", show_default=True),
    click.option("--language-tag", "language_tag", default="@language", show_default=True),
    click.option(
        "--with-optional-type",
        "optional_type",
        is_flag=True,
        help=(
            "Whether to allow the type property to be optional in JSON Schema. "
            "By default a type property is REQUIRED for all top-level records "
            "and for any nested records in the instance."
        ),
    ),
    click.option(
        "--no-subclasses",
        "no_subclasses",
        is_flag=True,
        help=(
            "Set this flag to generate a schema for only the specified record type "
            "and not the type and all of its subclasses."
        ),
    ),
    click.option(
        "--no-additional-properties",
        "no_additional_properties",
        is_flag=True,
        help=(
            "Set this flag to generate a JSON schema that allows only the properties "
            "defined in the record spec schema."
        ),
    ),
    click.option(
        "--allow-jsonld-context",
        "allow_json_ld_context",
        is_flag=True,
        help="Allows the @context property on records.",
    ),
    click.option(
        "--allow-json-schema-ref",
        "allow_json_schema_ref",
        is_flag=True,
        help="Allows the @schema reference to JSON schema to appear on records.",
    ),
    ]
    for option in reversed(options):
        command = option(command)
    return command


def _collect_catalog(catalog_pairs: tuple[str, ...]) -> dict[str, str]:
    catalog: dict[str, str] = {}
    for entry in catalog_pairs:
        if "=" not in entry:
            raise click.UsageError(f"Invalid --catalog entry {entry!r}: expected URI=URL")
        key, _, value = entry.partition("=")
        catalog[key] = value
    return catalog


def open_output(output: Path | None, mode: str = "w") -> Any:
    """Open the output file, defaulting to stdout (the Kotlin
    ``getOutputStream``). Returns a context manager."""
    if output is not None:
        return open(output, mode, encoding="utf-8")
    return sys.stdout


def write_json(output: Path | None, tree: dict[str, Any], indent: int | None = 2) -> None:
    """Write a JSON tree as indented JSON (mirrors the Kotlin JsonGenerator
    configuration: ESCAPE_NON_ASCII + INDENT_OUTPUT)."""
    with open_output(output) as out:
        json.dump(tree, out, indent=indent, ensure_ascii=True, default=str)
        out.write("\n")


def write_yaml(output: Path | None, tree: dict[str, Any]) -> None:
    """Write a tree as YAML (the Kotlin YAMLFactory with native type ids
    disabled — pyyaml does not emit them)."""
    with open_output(output) as out:
        yaml.safe_dump(tree, out, allow_unicode=False, sort_keys=False)


def write_rdf(output: Path | None, graph: Any, format: str) -> None:
    """Serialize an rdflib graph as Turtle or N-Triples."""
    rdflib_format = "turtle" if format.upper() in ("TTL", "TURTLE") else "nt"
    serialized = graph.serialize(format=rdflib_format)
    with open_output(output) as out:
        out.write(serialized)