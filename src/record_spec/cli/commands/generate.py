"""The ``generate`` subcommand: generate a JSON schema for record spec
itself, including all extension service provider schemas."""

from __future__ import annotations

from pathlib import Path

import click

from record_spec.cli.commands.common import write_json


@click.command()
@click.option(
    "-o",
    "--output",
    type=click.Path(path_type=Path),
    help="The output file to write to. If not specified output will be written to stdout.",
)
def generate(output: Path | None) -> None:
    """Generate a JSON schema for record spec which includes the base record
    spec schema plus all schema extensions provided by any extension service
    providers on the classpath (entry points)."""
    from record_spec.exceptions import RecordNotFoundException
    from record_spec.extensions import get_combined_schema
    from record_spec.jsonschema import JsonOptions, JsonSchemaBuilder

    schema = get_combined_schema()
    options = JsonOptions(
        bare_reference_ids=True,
        type_property="type",
        value_property="value",
        language_property="language",
        optional_type_property=True,
        additional_properties=False,
    )
    builder = JsonSchemaBuilder(options)
    schema_record = next((record for record in schema.records if record.short_code == "RecordSpecSchema"), None)
    if schema_record is None:
        raise click.UsageError("Could not find a record with short-code RecordSpecSchema in the merged schema")
    try:
        schema_node = builder.build(schema_record)
    except RecordNotFoundException as e:  # pragma: no cover - defensive
        raise click.UsageError(str(e)) from e
    write_json(output, schema_node)