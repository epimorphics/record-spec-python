"""Parse YAML (or JSON) schemas into a :class:`SchemaAdapter`."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import yaml

from record_spec.exceptions import SchemaReadException
from record_spec.serde.defs import SchemaDef

if TYPE_CHECKING:
    from record_spec.convert import SchemaAdapter

Source = str | bytes | Any


class YamlParser:
    """Parses a YAML (or JSON) schema source into a :class:`SchemaDef` adapter."""

    def parse(self, source: Source) -> SchemaAdapter:
        try:
            data = yaml.safe_load(source)
        except yaml.YAMLError as e:
            raise SchemaReadException(f"Error parsing YAML schema: {e}", e) from e
        try:
            return SchemaDef.from_dict(data).adapter
        except (KeyError, TypeError, ValueError) as e:
            raise SchemaReadException(f"Error reading YAML schema: {e}", e) from e


class JsonParser:
    """Parses a JSON schema source into a :class:`SchemaDef` adapter."""

    def parse(self, source: str | bytes) -> SchemaAdapter:
        import json

        try:
            data = json.loads(source)
        except (json.JSONDecodeError, TypeError) as e:
            raise SchemaReadException(f"Error parsing JSON schema: {e}", e) from e
        try:
            return SchemaDef.from_dict(data).adapter
        except (KeyError, TypeError, ValueError) as e:
            raise SchemaReadException(f"Error reading JSON schema: {e}", e) from e