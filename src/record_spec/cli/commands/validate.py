"""The ``validate`` subcommand."""

from __future__ import annotations

from pathlib import Path

import click

from record_spec.exceptions import SchemaValidationException

from .common import SchemaCommandMixin, schema_command_options


@click.command()
@click.argument("schema_files", type=click.Path(exists=True, path_type=Path), nargs=-1, required=True)
@schema_command_options
def validate(
    schema_files: tuple[Path,
    ...],
    from_format: str | None,
    catalog: tuple[str,
    ...],
    no_import: bool,
) -> None:
    """Validate a record-spec schema.

    The validation process ensures that all references to record and mixin
    definitions within a schema can be properly resolved and that the
    resulting resolved schema does not contain properties with invalid
    ranges due to inheritance of constraints.
    """
    from pathlib import Path

    command = _ValidateCommand()
    command.from_format = from_format
    command.schema_files = tuple(Path(p) for p in schema_files)
    command.catalog = catalog
    command.no_import = no_import
    command.run()


class _ValidateCommand(SchemaCommandMixin):
    def run(self) -> None:
        files = ", ".join(str(f.resolve()) for f in self.schema_files)
        click.echo(f"Validate schema at {files}")
        try:
            schema = self._load_schema()
            schema.validate()
            click.echo("Schema is valid.")
        except SchemaValidationException as e:
            error_list = list(e.validation_errors)
            if not error_list:
                click.echo(f"Schema validation failed: {e.message}")
            elif len(error_list) > 1:
                click.echo(f"{len(error_list)} validation errors:")
                for error in error_list:
                    click.echo(f"\t{error}")
            else:
                click.echo(f"Schema validation failed: {error_list[0]}")