"""Build an RDF graph of a schema from a :class:`SchemaAdapter`.

The rdflib-based equivalent of the Kotlin ``RdfBuilder``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rdflib import RDF, BNode, Graph, Literal, URIRef

from record_spec.model.property import PropertyKind
from record_spec.model.values import LangString, PrefixMapping
from record_spec.values.curi_resolver import CuriResolverImpl
from record_spec.values.datatypes import XSD

from .vocab import (
    REC_CONSTRAINT,
    REC_DATATYPE,
    REC_EXTENDS,
    REC_IDENTIFIER,
    REC_IMPLEMENTS,
    REC_IN,
    REC_KEY_PROPERTY,
    REC_LITERAL_CONSTRAINT,
    REC_LITERAL_PROPERTY,
    REC_MAX_EXCLUSIVE,
    REC_MAX_INCLUSIVE,
    REC_MIN_EXCLUSIVE,
    REC_MIN_INCLUSIVE,
    REC_MIXIN,
    REC_MIXIN_CLASS,
    REC_NESTED,
    REC_PATTERN,
    REC_PREFIX,
    REC_PREFIX_MAPPING,
    REC_PROPERTY,
    REC_PROPERTY_MAP,
    REC_RECORD,
    REC_RECORD_CONSTRAINT,
    REC_RECORD_PREDICATE,
    REC_RECORD_PROPERTY,
    REC_REPEATABLE,
    REC_REQUIRED,
    REC_REVERSED,
    REC_SCHEMA,
    REC_SHORT_CODE,
    REC_URI,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

    from rdflib.term import Node

    from record_spec.convert import (
        LiteralConstraintAdapter,
        MixinAdapter,
        PropertyAdapter,
        PropertyMappingAdapter,
        RecordAdapter,
        RecordConstraintAdapter,
        SchemaAdapter,
    )
    from record_spec.values import CuriResolver


def _create_typed_literal(value: str, datatype: str) -> Literal:
    """Create a literal with the given datatype (the Kotlin ``RdfUtils.createLiteral``)."""
    if datatype == XSD + "string":
        return Literal(value)
    return Literal(value, datatype=URIRef(datatype))


class RdfBuilder:
    """Builds an RDF graph of a schema from a :class:`SchemaAdapter`."""

    def __init__(self, graph: Graph, schema_uri: str):
        self.graph = graph
        self.schema_uri = schema_uri

    def build(self, schema_adapter: SchemaAdapter) -> None:
        schema_resource = URIRef(self.schema_uri)
        self._add(schema_resource, URIRef(RDF.type), URIRef(REC_SCHEMA))
        curi_resolver = CuriResolverImpl(
            {pm.prefix: pm.uri for pm in schema_adapter.prefixes},
            schema_adapter.base_uri,
        )
        if schema_adapter.identifier is not None:
            self._add(schema_resource, URIRef(REC_IDENTIFIER), URIRef(schema_adapter.identifier))
        for prefix_mapping in schema_adapter.prefixes:
            self._build_prefix_mapping(prefix_mapping, schema_resource)
        for record_adapter in schema_adapter.records:
            self._build_record(record_adapter, schema_resource, curi_resolver)
        for mixin_adapter in schema_adapter.mixins:
            self._build_mixin(mixin_adapter, schema_resource, curi_resolver)
        # NOTE: extension records are not written to RDF until M4 provides
        # the RDF record writer (the Kotlin build(ObjectNode) path uses
        # RdfRecordWriter). Tracked in the quirks ticket.

    def _build_prefix_mapping(self, prefix_mapping: PrefixMapping, schema: Node) -> None:
        mapping_resource = BNode()
        self._add(schema, URIRef(REC_PREFIX_MAPPING), mapping_resource)
        self._add(mapping_resource, URIRef(REC_PREFIX), Literal(prefix_mapping.prefix))
        self._add(mapping_resource, URIRef(REC_URI), Literal(prefix_mapping.uri))

    def _build_record(self, record_adapter: RecordAdapter, schema: Node, curi_resolver: CuriResolver) -> None:
        record_resource = URIRef(record_adapter.id)
        self._add(schema, URIRef(REC_RECORD_PREDICATE), record_resource)
        self._add(record_resource, URIRef(RDF.type), URIRef(REC_RECORD))
        self._add(record_resource, URIRef(REC_URI), URIRef(record_adapter.class_uri))
        self._add(record_resource, URIRef(REC_SHORT_CODE), Literal(record_adapter.short_code))
        # NOTE: the Kotlin RdfBuilder.addLangStrings creates the label/comment/
        # description statements but never adds them to the model, so
        # documentation is not serialized to RDF. That behaviour is mirrored
        # here: no rdfs:label / rdfs:comment / dct:description triples are
        # emitted. See issues/01-review-kotlin-quirks.md (quirk 8).
        if record_adapter.extends is not None:
            self._add(record_resource, URIRef(REC_EXTENDS), URIRef(curi_resolver.resolve(record_adapter.extends)))
        for mixin_id in record_adapter.mixins:
            self._add(record_resource, URIRef(REC_IMPLEMENTS), URIRef(curi_resolver.resolve(mixin_id)))
        for property_adapter in record_adapter.properties:
            property_resource = self._build_property(property_adapter, curi_resolver)
            self._add(record_resource, URIRef(REC_PROPERTY), property_resource)

    def _build_mixin(self, mixin_adapter: MixinAdapter, schema: Node, curi_resolver: CuriResolver) -> None:
        mixin_resource = URIRef(mixin_adapter.id)
        self._add(schema, URIRef(REC_MIXIN), mixin_resource)
        self._add(mixin_resource, URIRef(RDF.type), URIRef(REC_MIXIN_CLASS))
        # NOTE: documentation triples are not serialized (see _build_record).
        for property_adapter in mixin_adapter.properties:
            property_resource = self._build_property(property_adapter, curi_resolver)
            self._add(mixin_resource, URIRef(REC_PROPERTY), property_resource)

    def _build_property(self, property_adapter: PropertyAdapter, curi_resolver: CuriResolver) -> Node:
        property_resource = BNode()
        property_type = (
            REC_LITERAL_PROPERTY if property_adapter.kind == PropertyKind.LITERAL else REC_RECORD_PROPERTY
        )
        self._add(property_resource, URIRef(RDF.type), URIRef(property_type))
        self._add(property_resource, URIRef(REC_SHORT_CODE), Literal(property_adapter.short_code))
        self._add(property_resource, URIRef(REC_URI), URIRef(property_adapter.property_uri))
        if property_adapter.required:
            self._add(property_resource, URIRef(REC_REQUIRED), Literal(True))
        if property_adapter.repeatable:
            self._add(property_resource, URIRef(REC_REPEATABLE), Literal(True))
        if property_adapter.kind == PropertyKind.OBJECT:
            if property_adapter.reversed:
                self._add(property_resource, URIRef(REC_REVERSED), Literal(True))
            if property_adapter.nested:
                self._add(property_resource, URIRef(REC_NESTED), Literal(True))
        constraints = (
            [self._build_literal_constraint(c) for c in property_adapter.literal_constraints]
            if property_adapter.kind == PropertyKind.LITERAL
            else [self._build_record_constraint(c, curi_resolver) for c in property_adapter.record_constraints]
        )
        for constraint_resource in constraints:
            self._add(property_resource, URIRef(REC_CONSTRAINT), constraint_resource)
        if property_adapter.property_map is not None:
            self._add(
                property_resource,
                URIRef(REC_PROPERTY_MAP),
                self._build_property_map(property_adapter.property_map),
            )
        return property_resource

    def _build_property_map(self, property_map_adapter: PropertyMappingAdapter) -> Node:
        property_map_resource = BNode()
        self._add(property_map_resource, URIRef(REC_KEY_PROPERTY), Literal(property_map_adapter.key_property))
        return property_map_resource

    def _build_literal_constraint(self, literal_constraint: LiteralConstraintAdapter) -> Node:
        constraint_resource = BNode()
        datatype = literal_constraint.datatype
        datatype_resource = URIRef(datatype)
        self._add(constraint_resource, URIRef(RDF.type), URIRef(REC_LITERAL_CONSTRAINT))
        self._add(constraint_resource, URIRef(REC_DATATYPE), datatype_resource)
        if literal_constraint.pattern is not None:
            self._add(constraint_resource, URIRef(REC_PATTERN), Literal(literal_constraint.pattern))
        if literal_constraint.min_exclusive is not None:
            self._add(
                constraint_resource,
                URIRef(REC_MIN_EXCLUSIVE),
                _create_typed_literal(literal_constraint.min_exclusive, datatype),
            )
        if literal_constraint.max_exclusive is not None:
            self._add(
                constraint_resource,
                URIRef(REC_MAX_EXCLUSIVE),
                _create_typed_literal(literal_constraint.max_exclusive, datatype),
            )
        if literal_constraint.min_inclusive is not None:
            self._add(
                constraint_resource,
                URIRef(REC_MIN_INCLUSIVE),
                _create_typed_literal(literal_constraint.min_inclusive, datatype),
            )
        if literal_constraint.max_inclusive is not None:
            self._add(
                constraint_resource,
                URIRef(REC_MAX_INCLUSIVE),
                _create_typed_literal(literal_constraint.max_inclusive, datatype),
            )
        if literal_constraint.values_in is not None:
            for value in literal_constraint.values_in:
                self._add(constraint_resource, URIRef(REC_IN), _create_typed_literal(value, datatype))
        return constraint_resource

    def _build_record_constraint(
        self, record_constraint: RecordConstraintAdapter, curi_resolver: CuriResolver
    ) -> Node:
        constraint_resource = BNode()
        record_resource = URIRef(curi_resolver.resolve(record_constraint.record))
        self._add(constraint_resource, URIRef(RDF.type), URIRef(REC_RECORD_CONSTRAINT))
        self._add(constraint_resource, URIRef(REC_RECORD_PREDICATE), record_resource)
        if record_constraint.values_in is not None:
            for record_id in record_constraint.values_in:
                self._add(constraint_resource, URIRef(REC_IN), URIRef(record_id))
        return constraint_resource

    def _add(self, subject: Node, predicate: URIRef, obj: Node) -> None:
        self.graph.add((subject, predicate, obj))

    def _add_lang_strings(self, lang_strings: Iterable[LangString], predicate_uri: str, subject: Node) -> None:
        """Mirrors the Kotlin ``addLangStrings``, which creates the statements
        without adding them to the model: no triples are emitted."""
        for _lang_string in lang_strings:
            pass  # statement created but not added, as in the Kotlin original