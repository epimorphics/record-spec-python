"""Serialize a schema to an RDF serialization.

The rdflib-based equivalent of the Kotlin ``RdfSerializer``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rdflib import Graph

from record_spec.rdf.builder import RdfBuilder

if TYPE_CHECKING:
    import io

    from record_spec.convert import SchemaAdapter

#: The default schema URI used when building an RDF model of a schema.
DEFAULT_SCHEMA_URI = "http://example.org/spec/schema"


class RdfSerializer:
    """Utility wrapper around :class:`RdfBuilder` to write an RDF
    serialization of a schema.

    :param default_format: The default RDF format to write. Uses the format
        names supported by rdflib (plus the Jena-style aliases).
    """

    def __init__(self, default_format: str = "TTL"):
        self._default_format = default_format

    def write(self, writer: io.TextIOBase, schema_adapter: SchemaAdapter, format: str | None = None) -> None:
        """Write the RDF serialization of the specified schema using the
        default format configured for this serializer.

        :param writer: The text output writer to use.
        :param schema_adapter: The schema to be written.
        :param format: The RDF format to use for output.
            Defaults to this serializer's default format.
        """
        from record_spec.rdf.parser import _rdflib_format

        graph = Graph()
        builder = RdfBuilder(graph, DEFAULT_SCHEMA_URI)
        builder.build(schema_adapter)
        serialized = graph.serialize(format=_rdflib_format(format or self._default_format))
        writer.write(serialized)