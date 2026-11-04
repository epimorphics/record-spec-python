"""The ``convert`` subcommand."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import click

from record_spec.cli.commands.common import (
    DEFAULT_SCHEMA_URI,
    SchemaCommandMixin,
    schema_command_options,
    write_json,
    write_rdf,
    write_yaml,
)


class _ConvertCommand(SchemaCommandMixin):
    def __init__(self, to_form: str, output: Path | None):
        self.to_form = to_form
        self.output = output

    def run(self) -> None:
        files = ", ".join(str(f.resolve()) for f in self.schema_files)
        destination = str(self.output.resolve()) if self.output is not None else "stdout"
        click.echo(f"Convert from {files} to {self.to_form} writing to {destination}")
        schema = self._load_schema()
        schema.validate()
        if self.to_form == "yaml":
            self._write_yaml(schema)
        elif self.to_form == "json":
            self._write_json(schema)
        elif self.to_form == "ttl":
            self._write_rdf(schema, "TTL")
        elif self.to_form == "nt":
            self._write_rdf(schema, "NT")

    def _write_yaml(self, schema: Any) -> None:
        from record_spec.serde import SchemaDefBuilder

        write_yaml(self.output, SchemaDefBuilder().build(schema.adapter).to_dict())

    def _write_json(self, schema: Any) -> None:
        from record_spec.serde import SchemaDefBuilder

        write_json(self.output, SchemaDefBuilder().build(schema.adapter).to_dict())

    def _write_rdf(self, schema: Any, rdf_format: str) -> None:
        from rdflib import Graph

        from record_spec.rdf import RdfBuilder

        schema_uri = (
            schema.base_uri
            or (self.output.resolve().as_uri() if self.output is not None else None)
            or DEFAULT_SCHEMA_URI
        )
        graph = Graph()
        RdfBuilder(graph, schema_uri).build(schema.adapter)
        write_rdf(self.output, graph, rdf_format)


@click.command()
@click.argument("schema_files", type=click.Path(exists=True, path_type=Path), nargs=-1, required=True)
@click.option(
    "-t",
    "--to",
    "to_form",
    type=click.Choice(["yaml", "json", "ttl", "nt"]),
    default="yaml",
    show_default=True,
    help="The output form to convert to.",
)
@click.option(
    "-o",
    "--output",
    type=click.Path(path_type=Path),
    help="The output file to write to. If not specified output will be written to stdout.",
)
@schema_command_options
def convert(
    schema_files: tuple[Path,
    ...],
    to_form: str,
    output: Path | None,
    from_format: str | None,
    catalog: tuple[str,
    ...],
    no_import: bool,
) -> None:
    """Convert between different representations of a record-spec schema.

    Accepts and produces record-spec schemas in the following formats:

    \b
    * yaml - YAML syntax
    * json - JSON syntax
    * ttl  - RDF using Turtle 1.1 syntax
    * nt   - RDF using NTriples 1.1 syntax
    """
    command = _ConvertCommand(to_form, output)
    command.from_format = from_format
    command.schema_files = tuple(schema_files)
    command.catalog = catalog
    command.no_import = no_import
    command.run()