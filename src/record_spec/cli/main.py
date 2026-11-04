"""Console entry point: builds the command group and dispatches."""

from __future__ import annotations

import click

from record_spec.cli.commands.convert import convert
from record_spec.cli.commands.generate import generate
from record_spec.cli.commands.json_ld import json_ld
from record_spec.cli.commands.json_schema import json_schema
from record_spec.cli.commands.mapper import rdf_mapper
from record_spec.cli.commands.rdfs import rdfs
from record_spec.cli.commands.shacl import shacl
from record_spec.cli.commands.validate import validate


@click.group()
def record_spec() -> None:
    """Tools for processing record-spec schemas."""


record_spec.add_command(validate)
record_spec.add_command(convert)
record_spec.add_command(generate)
record_spec.add_command(json_schema)
record_spec.add_command(json_ld)
record_spec.add_command(shacl)
record_spec.add_command(rdfs)
record_spec.add_command(rdf_mapper)


def main() -> None:
    """Console-script entry point."""
    record_spec()


if __name__ == "__main__":
    main()