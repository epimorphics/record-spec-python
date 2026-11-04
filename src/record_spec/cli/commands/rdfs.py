"""The ``rdfs`` subcommand."""

from __future__ import annotations

from pathlib import Path

import click

from record_spec.cli.commands.common import SchemaCommandMixin, schema_command_options, write_rdf


class _RdfsCommand(SchemaCommandMixin):
    def __init__(self, to_form: str, output: Path | None, with_mixins: bool):
        self.to_form = to_form
        self.output = output
        self.with_mixins = with_mixins

    def run(self) -> None:
        from rdflib import Graph

        from record_spec.rdf import RdfsBuilder, RdfsOptions

        schema = self._load_schema()
        graph = Graph()
        graph.bind("sh", "http://www.w3.org/ns/shacl#")
        for prefix_mapping in schema.prefix_mappings:
            graph.bind(prefix_mapping.prefix, prefix_mapping.uri)
        builder = RdfsBuilder(graph, RdfsOptions(with_mixins=self.with_mixins))
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
    "-m",
    "--with-mixins",
    is_flag=True,
    help="Include mixins in the subclasses of each record class.",
)
@schema_command_options
def rdfs(
    schema_files: tuple[Path,
    ...],
    to_form: str,
    output: Path | None,
    with_mixins: bool,
    from_format: str | None,
    catalog: tuple[str,
    ...],
    no_import: bool,
) -> None:
    """Generate an RDFS/OWL ontology for a record-spec schema."""
    command = _RdfsCommand(to_form, output, with_mixins)
    command.from_format = from_format
    command.schema_files = tuple(schema_files)
    command.catalog = catalog
    command.no_import = no_import
    command.run()