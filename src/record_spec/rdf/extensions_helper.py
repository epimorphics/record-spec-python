"""Reads and matches RDF extension records (the Kotlin ``ExtensionsHelper``).

An extension record attached to a schema element via ``rec:extension`` is
read as a JSON tree using the record definition for its ``rdf:type`` from
the *combined* schema (the core record-spec schema merged with the schemas
provided by all registered extension services).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from rdflib import RDF, URIRef
from rdflib.term import Literal, Node

if TYPE_CHECKING:
    from rdflib import Graph

    from record_spec.model import Record, Schema


class ExtensionsHelper:
    """Matches RDF extension resources to extension record definitions and
    reads them as JSON trees."""

    def __init__(self) -> None:
        self._extension_records: dict[str, Record | None] = {}
        self._schema: Schema | None = None

    @property
    def schema(self) -> Schema:
        """The combined schema: core record-spec plus extension services."""
        if self._schema is None:
            from record_spec.extensions import get_combined_schema

            self._schema = get_combined_schema()
        return self._schema

    def record_for(self, graph: Graph, resource: Node) -> Record | None:
        """Return the extension record definition for a resource's first
        recognized ``rdf:type``, or None."""
        resource_types = [str(t) for t in graph.objects(resource, RDF.type) if isinstance(t, URIRef)]
        for resource_type in resource_types:
            if resource_type not in self._extension_records:
                self._extension_records[resource_type] = self._find_service_record(resource_type)
            record = self._extension_records[resource_type]
            if record is not None:
                return record
        return None

    def _find_service_record(self, resource_type: str) -> Record | None:
        return next((record for record in self.schema.records if record.class_uri == resource_type), None)

    def read_extension(self, graph: Graph, resource: Node) -> dict[str, Any] | None:
        """Read an extension resource as a JSON tree, or None if its type
        is not a recognized extension record type."""
        record = self.record_for(graph, resource)
        if record is None:
            return None
        from record_spec.rdf.record_reader import RdfRecordReader

        return RdfRecordReader(graph, self.schema).read_value(resource, record)

    def read_extensions(self, graph: Graph, resource: Node, extension_property: str) -> list[dict[str, Any]]:
        """Read all extension resources attached to a resource via the
        given extension predicate."""
        result: list[dict[str, Any]] = []
        for ext_resource in (
            obj for obj in graph.objects(resource, URIRef(extension_property)) if not isinstance(obj, Literal)
        ):
            tree = self.read_extension(graph, ext_resource)
            if tree is not None:
                result.append(tree)
        return result