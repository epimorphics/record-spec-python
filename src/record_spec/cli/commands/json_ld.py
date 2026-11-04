"""The ``json-ld`` subcommand."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import click

from record_spec.cli.commands.common import (
    JsonCommandMixin,
    json_command_options,
    schema_command_options,
    write_json,
)


class _JsonLdCommand(JsonCommandMixin):
    def __init__(self, record: str | None, output: Path | None):
        self.record = record
        self.output = output

    def run(self) -> None:
        from record_spec.jsonschema import JsonLdContextBuilder

        schema = self._load_schema()
        options = self._get_json_options()
        builder = JsonLdContextBuilder(options)
        if self.record is not None:
            context = builder.make_record_context(schema.resolve_record(self.record))
        else:
            context = builder.make_schema_context(schema)
        write_json(self.output, context)


@click.command(name="json-ld")
@click.argument("schema_files", type=click.Path(exists=True, path_type=Path), nargs=-1, required=True)
@click.option("-r", "--record", help="The short code or id of the record type to generate a JSON-LD context for")
@click.option("-o", "--output", type=click.Path(path_type=Path), help="The output file to write to")
@schema_command_options
@json_command_options
def json_ld(
    schema_files: tuple[Path, ...],
    record: str | None,
    output: Path | None,
    from_format: str | None,
    catalog: tuple[str, ...],
    no_import: bool,
    **json_flags: Any,
) -> None:
    """Generate a JSON-LD context that can be used to interpret a JSON document
    conforming to the record-spec schema as RDF using JSON-LD 1.1.

    The generated JSON-LD context uses the type property (by default `@type` -
    although this may be overridden on the command-line) to associate context
    information with the top-level record object and with any nested records
    contained in the document.

    By default the generated context covers all of the record definitions
    provided in the input schema. Using the --record option it is possible to
    narrow the scope of the context to cover only the specified record
    definition, record definitions that inherit from it and record definitions
    that are required to cover all nested properties.
    """
    command = _JsonLdCommand(record, output)
    command.from_format = from_format
    command.schema_files = tuple(schema_files)
    command.catalog = catalog
    command.no_import = no_import
    for key, value in json_flags.items():
        setattr(command, key, value)
    command.run()