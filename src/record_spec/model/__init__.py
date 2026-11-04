"""The record-spec model: `Schema`, `Record`, `Mixin`, properties and constraints."""

from record_spec.model.events import (
    Event,
    EventListener,
    EventSourceMixin,
    MixinModifiedEvent,
    PropertyModifiedEvent,
    RecordModifiedEvent,
)
from record_spec.model.schema import Schema
from record_spec.model.schema_builder import SchemaBuilder

from .base import Documentable, Extensible, PropertyFactory
from .constraints import LiteralConstraint, RecordConstraint
from .mixin import Mixin
from .property import LiteralProperty, Property, PropertyKind, RecordProperty
from .property_mapping import PropertyMapping
from .record import Record
from .resolvers import MixinResolver, RecordResolver
from .values import LangString, PrefixMapping

__all__ = [
    "Schema",
    "SchemaBuilder",
    "Record",
    "RecordResolver",
    "Mixin",
    "MixinResolver",
    "Property",
    "PropertyKind",
    "LiteralProperty",
    "RecordProperty",
    "PropertyMapping",
    "LiteralConstraint",
    "RecordConstraint",
    "Documentable",
    "Extensible",
    "PropertyFactory",
    "LangString",
    "PrefixMapping",
    "Event",
    "EventListener",
    "EventSourceMixin",
    "RecordModifiedEvent",
    "MixinModifiedEvent",
    "PropertyModifiedEvent",
]