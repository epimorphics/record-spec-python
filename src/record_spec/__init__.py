"""record-spec: a schema language for defining record-like views of RDF data.

Pure-Python implementation of the record-spec schema language, translated from
the Kotlin original (``com.epimorphics:record-spec``).
"""

from record_spec import exceptions
from record_spec.convert import (
    LiteralConstraintAdapter,
    MixinAdapter,
    PropertyAdapter,
    PropertyMappingAdapter,
    RecordAdapter,
    RecordConstraintAdapter,
    SchemaAdapter,
)
from record_spec.model import (
    Documentable,
    Event,
    EventListener,
    EventSourceMixin,
    Extensible,
    LangString,
    LiteralConstraint,
    LiteralProperty,
    Mixin,
    MixinModifiedEvent,
    MixinResolver,
    PrefixMapping,
    Property,
    PropertyKind,
    PropertyMapping,
    Record,
    RecordConstraint,
    RecordModifiedEvent,
    RecordProperty,
    RecordResolver,
    Schema,
    SchemaBuilder,
)
from record_spec.serde import (
    LangStringDef,
    LiteralConstraintDef,
    LiteralPropertyDef,
    MixinDef,
    PrefixMappingDef,
    PropertyMappingDef,
    RecordConstraintDef,
    RecordDef,
    RecordPropertyDef,
    SchemaDef,
    SchemaDefBuilder,
)
from record_spec.values import RDF_LANG_STRING, XSD, Comparator, Datatype, Datatypes
from record_spec.yaml_parser import JsonParser, YamlParser

__version__ = "0.1.0"

__all__ = [
    "exceptions",
    # model
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
    "LangString",
    "PrefixMapping",
    "Event",
    "EventListener",
    "EventSourceMixin",
    "RecordModifiedEvent",
    "MixinModifiedEvent",
    # convert
    "SchemaAdapter",
    "RecordAdapter",
    "MixinAdapter",
    "PropertyAdapter",
    "LiteralConstraintAdapter",
    "RecordConstraintAdapter",
    "PropertyMappingAdapter",
    # serde
    "SchemaDef",
    "SchemaDefBuilder",
    "RecordDef",
    "MixinDef",
    "LiteralPropertyDef",
    "RecordPropertyDef",
    "LiteralConstraintDef",
    "RecordConstraintDef",
    "PropertyMappingDef",
    "PrefixMappingDef",
    "LangStringDef",
    # values
    "XSD",
    "RDF_LANG_STRING",
    "Comparator",
    "Datatype",
    "Datatypes",
    # parsers
    "YamlParser",
    "JsonParser",
]