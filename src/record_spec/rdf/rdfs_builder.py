"""Builds an RDFS/OWL ontology graph from a record-spec schema (the Kotlin ``RdfsBuilder``)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from rdflib import RDF, Graph, URIRef

if TYPE_CHECKING:
    from record_spec.model import Record, Schema

RDFS = "http://www.w3.org/2000/01/rdf-schema#"
RDFS_CLASS = RDFS + "Class"
RDFS_SUB_CLASS_OF = RDFS + "subClassOf"


@dataclass
class RdfsOptions:
    """Options controlling RDFS generation (the Kotlin ``RdfsBuilder.Options``)."""

    #: Whether to also emit ``rdfs:subClassOf`` statements for the mixins
    #: implemented by each record.
    with_mixins: bool = False


class RdfsBuilder:
    """Builds an RDFS model from a :class:`Schema`."""

    def __init__(self, graph: Graph, options: RdfsOptions | None = None):
        self.graph = graph
        self.options = options if options is not None else RdfsOptions()

    def build(self, schema: Schema) -> None:
        for record in schema.records:
            self.build_record(record)

    def build_record(self, record: Record) -> None:
        graph = self.graph
        cls = URIRef(record.class_uri)
        graph.add((cls, RDF.type, URIRef(RDFS_CLASS)))
        if record.parent is not None:
            graph.add((cls, URIRef(RDFS_SUB_CLASS_OF), URIRef(record.parent.class_uri)))
        if self.options.with_mixins:
            for mixin in record.mixins:
                graph.add((cls, URIRef(RDFS_SUB_CLASS_OF), URIRef(mixin.id)))