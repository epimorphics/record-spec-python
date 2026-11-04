"""RDF support: parsing schemas from RDF, and serializing schemas to RDF.

The rdflib-based equivalent of the Kotlin ``rdf`` package.
"""

from record_spec.rdf.adapters import (
    RdfLiteralConstraintAdapter,
    RdfMixinAdapter,
    RdfPropertyAdapter,
    RdfPropertyMappingAdapter,
    RdfRecordAdapter,
    RdfRecordConstraintAdapter,
    RdfSchemaAdapter,
)
from record_spec.rdf.builder import RdfBuilder
from record_spec.rdf.parser import FORMAT_ALIASES, RdfParser
from record_spec.rdf.rdf_utils import create_literal
from record_spec.rdf.rdfs_builder import RdfsBuilder, RdfsOptions
from record_spec.rdf.serializer import DEFAULT_SCHEMA_URI, RdfSerializer
from record_spec.rdf.shacl_builder import ShaclBuilder, ShaclOptions
from record_spec.rdf.vocab import Vocab

__all__ = [
    "RdfParser",
    "RdfBuilder",
    "RdfSerializer",
    "DEFAULT_SCHEMA_URI",
    "FORMAT_ALIASES",
    "RdfSchemaAdapter",
    "RdfRecordAdapter",
    "RdfMixinAdapter",
    "RdfPropertyAdapter",
    "RdfLiteralConstraintAdapter",
    "RdfRecordConstraintAdapter",
    "RdfPropertyMappingAdapter",
    "Vocab",
    "ShaclBuilder",
    "ShaclOptions",
    "RdfsBuilder",
    "RdfsOptions",
    "create_literal",
]