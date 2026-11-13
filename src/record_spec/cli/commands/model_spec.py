"""The ``model-spec`` subcommand."""

from __future__ import annotations

from pathlib import Path

import click

from record_spec.cli.commands.common import SchemaCommandMixin, open_output, schema_command_options


class _ModelSpecCommand(SchemaCommandMixin):
    def __init__(self, include_mixins: bool, type_property: str, output: Path | None):
        self.include_mixins = include_mixins
        self.type_property = type_property
        self.output = output

    def run(self) -> None:
        from record_spec.modelspec import ModelSpecBuilder, ModelSpecOptions

        schema = self._load_schema()
        builder = ModelSpecBuilder(
            ModelSpecOptions(include_mixins=self.include_mixins, type_property=self.type_property)
        )
        yaml_text = builder.write_yaml(schema)
        with open_output(self.output) as out:
            out.write(yaml_text)


@click.command(name="model-spec")
@click.argument("schema_files", type=click.Path(exists=True, path_type=Path), nargs=-1, required=True)
@click.option(
    "--include-mixins",
    is_flag=True,
    help="Include mixin definitions as classes, and as the super-classes of the records that use them",
)
@click.option(
    "--type-property",
    default="@type",
    show_default=True,
    help="The name to use for the synthetic rdf:type property added to every class",
)
@click.option("-o", "--output", type=click.Path(path_type=Path), help="The output file to write to")
@schema_command_options
def model_spec(
    schema_files: tuple[Path, ...],
    include_mixins: bool,
    type_property: str,
    output: Path | None,
    from_format: str | None,
    catalog: tuple[str, ...],
    no_import: bool,
) -> None:
    """Generate a model-spec definition (YAML) from a record-spec schema.

    The generated model-spec describes the same classes and properties as
    the source record-spec schema. Mixin definitions are not included by
    default: use --include-mixins to emit them as classes in their own
    right, and to emit the mixins used by a record as its super-classes.

    Each generated class includes a synthetic rdf:type property, named
    @type by default, which may be renamed using --type-property.
    """
    command = _ModelSpecCommand(include_mixins, type_property, output)
    command.from_format = from_format
    command.schema_files = tuple(schema_files)
    command.catalog = catalog
    command.no_import = no_import
    command.run()
