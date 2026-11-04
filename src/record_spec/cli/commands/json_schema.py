"""The ``json-schema`` subcommand."""

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


class _JsonSchemaCommand(JsonCommandMixin):
    def __init__(self, record: str | None, output: Path | None):
        self.record = record
        self.output = output

    def run(self) -> None:
        from record_spec.exceptions import RecordNotFoundException
        from record_spec.jsonschema import JsonSchemaBuilder

        schema = self._load_schema()
        options = self._get_json_options()
        builder = JsonSchemaBuilder(options)
        record_id = self.record
        if record_id is None:
            raise click.UsageError(
                "Generating a complete JSON Schema for a record-spec schema is not yet implemented.",
            )
        try:
            schema_node = builder.build(schema.resolve_record(record_id))
        except RecordNotFoundException:
            raise click.UsageError(
                f"A record with the short-code '{self.record}' was not found in the schema."
            ) from None
        write_json(self.output, schema_node)


@click.command(name="json-schema")
@click.argument("schema_files", type=click.Path(exists=True, path_type=Path), nargs=-1, required=True)
@click.option("-r", "--record", help="The short code or id of the record type to generate a JSON schema for")
@click.option("-o", "--output", type=click.Path(path_type=Path), help="The output file to write to")
@schema_command_options
@json_command_options
def json_schema(
    schema_files: tuple[Path, ...],
    record: str | None,
    output: Path | None,
    from_format: str | None,
    catalog: tuple[str, ...],
    no_import: bool,
    **json_flags: Any,
) -> None:
    """Generate a JSON schema that can validate that a JSON document conforms
    to a specific record-spec schema.

    This tool generates a schema that can be used to validate a JSON document
    that is expected to contain a single instance of any one of the record
    definitions defined by the schema. Optionally the generated schema can be
    constrained validate only a specific record definition type.
    """
    command = _JsonSchemaCommand(record, output)
    command.from_format = from_format
    command.schema_files = tuple(schema_files)
    command.catalog = catalog
    command.no_import = no_import
    for key, value in json_flags.items():
        setattr(command, key, value)
    command.run()