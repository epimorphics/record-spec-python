"""The ``rdfmapper`` subcommand."""

from __future__ import annotations

from pathlib import Path

import click

from record_spec.cli.commands.common import (
    SchemaCommandMixin,
    schema_command_options,
    write_yaml,
)


class _RdfMapperCommand(SchemaCommandMixin):
    def __init__(self, record: str, output: Path | None, graph_add_pattern: str | None, graph_pattern: str | None):
        self.record = record
        self.output = output
        self.graph_add_pattern = graph_add_pattern
        self.graph_pattern = graph_pattern

    def run(self) -> None:
        from record_spec.exceptions import RecordNotFoundException
        from record_spec.rdfmapper import RdfMapperBuilder, RdfMapperOptions

        schema = self._load_schema()
        if self.graph_add_pattern is not None and self.graph_pattern is not None:
            raise click.UsageError(
                "The --graph and --graph-add options are mutually exclusive. "
                "Please specify EITHER --graph OR --graph-add."
            )
        options = RdfMapperOptions(
            graph_pattern=self.graph_pattern or self.graph_add_pattern,
            graph_add=self.graph_add_pattern is not None,
        )
        builder = RdfMapperBuilder(options)
        try:
            record = schema.resolve_record(self.record)
        except RecordNotFoundException:
            raise click.UsageError(
                f"A record with the short-code '{self.record}' was not found in the schema."
            ) from None
        mapping = builder.build(schema, record)
        write_yaml(self.output, mapping.to_dict())


@click.command(name="rdfmapper")
@click.argument("schema_files", type=click.Path(exists=True, path_type=Path), nargs=-1, required=True)
@click.argument("record", default=None, required=False)
@click.option("-o", "--output", type=click.Path(path_type=Path), help="The output file to write to")
@click.option("--graph-add", help="The pattern to identify the graph to add the mapped resource updates to.")
@click.option(
    "--graph",
    "graph_pattern",
    help="The pattern to identify the graph that will be replaced with the mapped resource updates.",
)
@schema_command_options
def rdf_mapper(
    schema_files: tuple[Path, ...],
    record: str | None,
    output: Path | None,
    graph_add: str | None,
    graph_pattern: str | None,
    from_format: str | None,
    catalog: tuple[str, ...],
    no_import: bool,
) -> None:
    """Generate an rdf-mapper template that converts a JSON instance of a
    record schema to RDF.

    RECORD is the short code or id of the record type to generate a mapping
    schema for.
    """
    if record is None:
        raise click.UsageError("Missing argument 'RECORD'.")
    command = _RdfMapperCommand(record, output, graph_add, graph_pattern)
    command.from_format = from_format
    command.schema_files = tuple(schema_files)
    command.catalog = catalog
    command.no_import = no_import
    command.run()