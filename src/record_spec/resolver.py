"""Schema resolution for `imports:` processing.

Resolvers retrieve a schema model by URI. They are used by
:meth:`Schema.resolve_imports` to retrieve imported schemas
(which may themselves have imports, resolved transitively).
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
from urllib.parse import urljoin
from urllib.request import Request, urlopen

import yaml

from record_spec.exceptions import SchemaReadException
from record_spec.serde.defs import SchemaDef

if TYPE_CHECKING:
    from record_spec.model import Schema

#: The Accept header value sent when retrieving schema resources.
SCHEMA_CONTENT_TYPES = "application/json; application/yaml"


class SchemaResolver(ABC):
    """The interface implemented by objects that can retrieve a schema by URI."""

    @abstractmethod
    def resolve(self, uri: str) -> Schema:
        """Retrieve the schema identified by ``uri``."""


class BasicSchemaResolver(SchemaResolver):
    """A :class:`SchemaResolver` that retrieves schemas over the web (or
    from the local filesystem via ``file:`` URLs), dispatching on the
    response content type: JSON resources are parsed as JSON, anything else
    as YAML.

    :param base_uri: The base URI to resolve relative import URIs against.
    """

    def __init__(self, base_uri: str):
        self._base_uri = base_uri

    def resolve(self, uri: str) -> Schema:
        url = urljoin(self._base_uri, uri)
        request = Request(url, headers={"Accept": SCHEMA_CONTENT_TYPES})
        with urlopen(request) as response:
            content_type = response.headers.get_content_type() if response.headers else None
            data = response.read()
        if content_type == "application/json":
            return self._load_json(data, url)
        return self._load_yaml(data, url)

    @staticmethod
    def _load_json(data: bytes, source_url: str) -> Schema:
        from record_spec.model import SchemaBuilder

        try:
            schema_def = SchemaDef.from_dict(json.loads(data))
        except (ValueError, TypeError) as e:
            raise SchemaReadException(f"Error reading JSON schema: {e}", e) from e
        return SchemaBuilder().build(schema_def.adapter, source_url, validate=False)

    @staticmethod
    def _load_yaml(data: bytes, source_url: str) -> Schema:
        from record_spec.model import SchemaBuilder

        try:
            schema_def = SchemaDef.from_dict(yaml.safe_load(data))
        except (ValueError, TypeError) as e:
            raise SchemaReadException(f"Error reading YAML schema: {e}", e) from e
        return SchemaBuilder().build(schema_def.adapter, source_url, validate=False)


class CachingSchemaResolver(SchemaResolver):
    """A :class:`SchemaResolver` decorator that caches resolved schemas by URI."""

    def __init__(self, base_resolver: SchemaResolver):
        self._base_resolver = base_resolver
        self._cache: dict[str, Schema] = {}

    def resolve(self, uri: str) -> Schema:
        if uri not in self._cache:
            self._cache[uri] = self._base_resolver.resolve(uri)
        return self._cache[uri]


class CatalogResolver(SchemaResolver):
    """Uses a catalog of URI mappings to redirect requests for a schema.

    :param catalog: A map of request URI to resource location URI.
    :param inner: The resolver to use to do the actual resource loading.
    """

    def __init__(self, catalog: dict[str, str], inner: SchemaResolver):
        self._catalog = catalog
        self._inner = inner

    def resolve(self, uri: str) -> Schema:
        if uri in self._catalog:
            return self._inner.resolve(self._catalog[uri])
        return self._inner.resolve(uri)