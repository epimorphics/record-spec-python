"""Parse RDF serializations of schemas into a :class:`SchemaAdapter`.

The rdflib-based equivalent of the Kotlin ``RdfParser``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from rdflib import RDF, URIRef

from record_spec.exceptions import RdfParserException, SchemaReadException
from record_spec.rdf.adapters import RdfSchemaAdapter
from record_spec.rdf.vocab import REC_SCHEMA

if TYPE_CHECKING:

    from record_spec.convert import SchemaAdapter

#: Jena-style format names mapped to rdflib format names.
FORMAT_ALIASES = {
    "TTL": "turtle",
    "TURTLE": "turtle",
    "N3": "n3",
    "N-TRIPLE": "nt",
    "NTRIPLE": "nt",
    "N-QUADS": "nquads",
    "RDF/XML": "xml",
    "RDFXML": "xml",
    "JSON-LD": "json-ld",
    "TRIG": "trig",
}

#: Anything that can be parsed as RDF: a string/bytes or a file-like object.
Source = str | bytes | Any


def _rdflib_format(format: str) -> str:
    return FORMAT_ALIASES.get(format.upper(), format)


class RdfParser:
    """Parses an RDF serialization of a schema into a :class:`SchemaAdapter`.

    :param default_format: The default RDF format to use when parsing a
        source. Allows any of the RDF format specifiers supported by rdflib
        (plus the Jena-style aliases in :data:`FORMAT_ALIASES`).
    """

    def __init__(self, default_format: str = "TTL"):
        self._default_format = default_format

    def parse(
        self,
        source: Source,
        base_uri: str,
        format: str | None = None,
        resource_uri: str | None = None,
    ) -> SchemaAdapter:
        """Parse the RDF from ``source`` to create a new :class:`SchemaAdapter`.

        :param source: The input (bytes/str or file-like) to parse from.
        :param base_uri: The default base URI to use for resolving relative
            URIs. May be overridden by the parsed schema.
        :param format: The RDF format to parse the input as.
            Defaults to this parser's default format.
        :param resource_uri: The IRI of the schema resource within the model,
            if the model contains more than one (or to be explicit).
        :return: A :class:`RdfSchemaAdapter` that wraps the parsed RDF graph.
        :raises RdfParserException: if no schema resource is found, or if
            multiple schema resources are found and no ``resource_uri`` is
            given.
        """
        from rdflib import Graph

        graph = Graph()
        data = source if isinstance(source, (str, bytes)) else source.read()
        try:
            graph.parse(data=data, publicID=base_uri, format=_rdflib_format(format or self._default_format))
        except Exception as e:  # noqa: BLE001 - rdflib raises many parser errors
            raise SchemaReadException(f"Error reading RDF schema: {e}", e) from e

        if resource_uri is not None:
            schema_resource = URIRef(resource_uri)
            if any(graph.triples((schema_resource, None, None))):
                return RdfSchemaAdapter(graph, schema_resource, base_uri)
            raise RdfParserException(f"No schema resource with IRI {resource_uri} found in the provided model.")

        schema_resources = list(graph.subjects(RDF.type, URIRef(REC_SCHEMA)))
        match len(schema_resources):
            case 0:
                raise RdfParserException("No schema found in model")
            case 1:
                return RdfSchemaAdapter(graph, schema_resources[0], base_uri)
            case _:
                raise RdfParserException(
                    "Multiple schema resource found. Specify the IRI of the schema resource to be parsed."
                )