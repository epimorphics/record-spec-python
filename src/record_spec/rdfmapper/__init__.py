"""rdf-mapper template generation."""

from record_spec.rdfmapper.builder import RdfMapperBuilder
from record_spec.rdfmapper.model import (
    IdMapping,
    IriMapping,
    LiteralPropertyValue,
    MapTo,
    PropertyValue,
    RdfMapperModel,
    ResourceTemplate,
    SimpleMapTo,
)
from record_spec.rdfmapper.options import RdfMapperOptions

__all__ = [
    "RdfMapperOptions",
    "RdfMapperBuilder",
    "RdfMapperModel",
    "ResourceTemplate",
    "PropertyValue",
    "IdMapping",
    "IriMapping",
    "LiteralPropertyValue",
    "MapTo",
    "SimpleMapTo",
]