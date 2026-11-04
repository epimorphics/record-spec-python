"""The ``shacl`` subcommand."""

from __future__ import annotations

from pathlib import Path

import click

from record_spec.cli.commands.common import SchemaCommandMixin, schema_command_options, write_rdf


class _ShaclCommand(SchemaCommandMixin):
    def __init__(
        self,
        to_form: str,
        output: Path | None,
        closed: bool,
        with_reference_type_validation: bool,
        exclude_records: tuple[str, ...],
    ):
        self.to_form = to_form
        self.output = output
        self.closed = closed
        self.with_reference_type_validation = with_reference_type_validation
        self.exclude_records = exclude_records

    def run(self) -> None:
        from rdflib import Graph

        from record_spec.rdf import ShaclBuilder, ShaclOptions

        schema = self._load_schema()
        graph = Graph()
        graph.bind("sh", "http://www.w3.org/ns/shacl#")
        for prefix_mapping in schema.prefix_mappings:
            graph.bind(prefix_mapping.prefix, prefix_mapping.uri)
        builder = ShaclBuilder(
            graph,
            ShaclOptions(
                closed=self.closed,
                validate_reference_types=self.with_reference_type_validation,
                exclude_records=list(self.exclude_records) or None,
            ),
        )
        builder.build(schema)
        write_rdf(self.output, graph, "TTL" if self.to_form == "ttl" else "NT")


@click.command()
@click.argument("schema_files", type=click.Path(exists=True, path_type=Path), nargs=-1, required=True)
@click.option(
    "-t",
    "--to",
    "to_form",
    type=click.Choice(["ttl", "nt"]),
    default="ttl",
    show_default=True,
    help="The output RDF format to write",
)
@click.option("-o", "--output", type=click.Path(path_type=Path), help="The output file to write to")
@click.option(
    "-c",
    "--closed",
    is_flag=True,
    help=(
        "Write a closed SHACL schema that does not allow properties not "
        "defined by the source record-spec schema."
    ),
)
@click.option(
    "-r",
    "--with-reference-type-validation",
    is_flag=True,
    help="Add constraints that require referenced resources to be of the expected type.",
)
@click.option(
    "-x",
    "--exclude-record",
    "exclude_records",
    multiple=True,
    help="The identifier of a record to be excluded from the SHACL validation.",
)
@schema_command_options
def shacl(
    schema_files: tuple[Path,
    ...],
    to_form: str,
    output: Path | None,
    closed: bool,
    with_reference_type_validation: bool,
    exclude_records: tuple[str,
    ...],
    from_format: str | None,
    catalog: tuple[str,
    ...],
    no_import: bool,
) -> None:
    """Generate SHACL shapes for a record-spec schema."""
    command = _ShaclCommand(
        to_form,
        output,
        closed,
        with_reference_type_validation,
        tuple(exclude_records),
    )
    command.from_format = from_format
    command.schema_files = tuple(schema_files)
    command.catalog = catalog
    command.no_import = no_import
    command.run()