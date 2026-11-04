"""Builds an SHACL shapes graph from a record-spec schema (the Kotlin ``ShaclBuilder``)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from rdflib import RDF, BNode, Graph, Literal, URIRef
from rdflib.namespace import XSD

from record_spec.model.constraints import LiteralConstraint
from record_spec.model.property import LiteralProperty, Property, RecordProperty
from record_spec.rdf.rdf_utils import create_literal as _typed_literal

if TYPE_CHECKING:
    from collections.abc import Iterable

    from rdflib.term import Node

    from record_spec.model import Record, RecordConstraint, Schema

SHACL = "http://www.w3.org/ns/shacl#"

SH_BLANK_NODE_OR_IRI = SHACL + "BlankNodeOrIRI"
SH_CLASS = SHACL + "class"
SH_CLOSED = SHACL + "closed"
SH_DATATYPE = SHACL + "datatype"
SH_IGNORED_PROPERTIES = SHACL + "ignoredProperties"
SH_IN = SHACL + "in"
SH_INVERSE_PATH = SHACL + "inversePath"
SH_LITERAL = SHACL + "Literal"
SH_MAX_COUNT = SHACL + "maxCount"
SH_MAX_EXCLUSIVE = SHACL + "maxExclusive"
SH_MAX_INCLUSIVE = SHACL + "maxInclusive"
SH_MESSAGE = SHACL + "message"
SH_MIN_COUNT = SHACL + "minCount"
SH_MIN_EXCLUSIVE = SHACL + "minExclusive"
SH_MIN_INCLUSIVE = SHACL + "minInclusive"
SH_NODE_KIND = SHACL + "nodeKind"
SH_NODE_SHAPE = SHACL + "NodeShape"
SH_OR = SHACL + "or"
SH_PATH = SHACL + "path"
SH_PATTERN = SHACL + "pattern"
SH_PROPERTY = SHACL + "property"
SH_SHAPE = SHACL + "shape"
SH_TARGET_CLASS = SHACL + "targetClass"


@dataclass
class ShaclOptions:
    """Options controlling SHACL generation (the Kotlin ``ShaclBuilder.Options``)."""

    #: Whether to generate record shapes as closed shapes.
    closed: bool = False

    #: Whether to validate the class of the value of reference properties.
    #: If True, SHACL validation asserts that the value of a reference
    #: property must be an instance of one of the RDF classes associated with
    #: the referenced record type(s); otherwise validation only ensures that
    #: the value is a URI or blank node.
    validate_reference_types: bool = False

    #: A list of the IDs of records to be excluded from the validation.
    #: No node shape will be generated for these records, and the record will
    #: be excluded from any type validation on nested or reference properties.
    exclude_records: list[str] | None = None


def _make_rdf_list(graph: Graph, values: Iterable[Node]) -> Node:
    """Build an RDF collection (list) from an iterable of nodes."""
    values = list(values)
    if not values:
        return RDF.nil
    head = BNode()
    current = head
    for ix, value in enumerate(values):
        graph.add((current, RDF.first, value))
        if ix < len(values) - 1:
            nxt = BNode()
            graph.add((current, RDF.rest, nxt))
            current = nxt
        else:
            graph.add((current, RDF.rest, RDF.nil))
    return head


class ShaclBuilder:
    """Builds an SHACL shapes graph from a :class:`Schema`."""

    def __init__(self, graph: Graph, options: ShaclOptions | None = None):
        self.graph = graph
        self.options = options if options is not None else ShaclOptions()

    def build(self, schema: Schema) -> None:
        excluded_records = [schema.resolve_record(record_id) for record_id in (self.options.exclude_records or [])]
        for record in schema.records:
            if record in excluded_records:
                continue
            self._build_record(record, excluded_records)

    def _build_record(self, record: Record, excluded_records: list[Record]) -> None:
        graph = self.graph
        record_resource = URIRef(record.id)
        graph.add((record_resource, RDF.type, URIRef(SH_NODE_SHAPE)))
        graph.add((record_resource, URIRef(SH_TARGET_CLASS), URIRef(record.class_uri)))
        if self.options.closed:
            graph.add((record_resource, URIRef(SH_CLOSED), Literal(True)))
            graph.add((record_resource, URIRef(SH_IGNORED_PROPERTIES), _make_rdf_list(graph, [URIRef(RDF.type)])))
        for prop in record.effective_properties:
            for shape in self._build_property_shapes(record_resource, prop, excluded_records):
                self._assert_property_path(shape, prop)
                graph.add((record_resource, URIRef(SH_PROPERTY), shape))

    def _assert_property_path(self, shape: Node, prop: Property) -> None:
        graph = self.graph
        if isinstance(prop, RecordProperty) and prop.reversed:
            inverse_path = BNode()
            graph.add((shape, URIRef(SH_PATH), inverse_path))
            graph.add((inverse_path, URIRef(SH_INVERSE_PATH), URIRef(prop.property_uri)))
        else:
            graph.add((shape, URIRef(SH_PATH), URIRef(prop.property_uri)))

    def _make_child_resource(self, parent_resource: Node, child_id: str) -> Node:
        if isinstance(parent_resource, BNode):
            return BNode(f"{parent_resource}.{child_id}")
        if isinstance(parent_resource, URIRef):
            base = str(parent_resource)
            if "#" in base:
                return URIRef(f"{base}-{child_id}")
            return URIRef(f"{base}#{child_id}")
        raise ValueError(f"{parent_resource} must be either an anonymous node or a URI node")

    def _build_property_shapes(
        self, parent_resource: Node, prop: Property, excluded_records: list[Record]
    ) -> list[Node]:
        graph = self.graph
        ret: list[Node] = []
        if prop.required or not prop.repeatable:
            cardinality_shape = self._make_child_resource(parent_resource, f"{prop.short_code}-count")
            ret.append(cardinality_shape)
            if prop.required:
                graph.add((cardinality_shape, URIRef(SH_MIN_COUNT), _typed_literal("1", str(XSD.integer))))
            if not prop.repeatable:
                graph.add((cardinality_shape, URIRef(SH_MAX_COUNT), _typed_literal("1", str(XSD.integer))))
            if prop.repeatable:
                pattern_expectation = "1 or more" if prop.required else "0 or more"
            else:
                pattern_expectation = "exactly 1" if prop.required else "0 or 1"
            count_of = (
                "Invalid count of incoming "
                if isinstance(prop, RecordProperty) and prop.reversed
                else "Invalid count of "
            )
            message = f"{count_of}{prop.property_uri} on target shape. Expected {pattern_expectation}."
            graph.add((cardinality_shape, URIRef(SH_MESSAGE), Literal(message, lang="en")))
        if isinstance(prop, LiteralProperty):
            ret.extend(self._make_literal_constraints(parent_resource, prop))
        elif isinstance(prop, RecordProperty):
            ret.extend(self._add_record_constraints(parent_resource, prop, excluded_records))
        return ret

    def _make_literal_constraints(self, parent_resource: Node, property_: LiteralProperty) -> list[Node]:
        graph = self.graph
        ret: list[Node] = []
        property_is_literal = self._make_child_resource(parent_resource, f"{property_.short_code}-kind")
        graph.add((property_is_literal, URIRef(SH_NODE_KIND), URIRef(SH_LITERAL)))
        ret.append(property_is_literal)

        if property_.constraints:
            literal_constraints_resource = self._make_child_resource(parent_resource, f"{property_.short_code}-value")
            if len(property_.constraints) == 1:
                self._make_literal_constraint_shape(literal_constraints_resource, property_.constraints[0])
                ret.append(literal_constraints_resource)
            else:
                children = []
                for ix, literal_constraint in enumerate(property_.constraints):
                    child = self._make_child_resource(parent_resource, f"{property_.short_code}-value-{ix}")
                    self._make_literal_constraint_shape(child, literal_constraint)
                    children.append(child)
                graph.add((literal_constraints_resource, URIRef(SH_OR), _make_rdf_list(graph, children)))
                ret.append(literal_constraints_resource)
        return ret

    def _make_literal_constraint_shape(self, constraint_resource: Node, literal_constraint: LiteralConstraint) -> None:
        graph = self.graph
        graph.add((constraint_resource, URIRef(SH_DATATYPE), URIRef(literal_constraint.datatype)))
        if literal_constraint.pattern is not None:
            graph.add((constraint_resource, URIRef(SH_PATTERN), Literal(literal_constraint.pattern)))
        if literal_constraint.min_inclusive is not None:
            graph.add(
                (
                    constraint_resource,
                    URIRef(SH_MIN_INCLUSIVE),
                    _typed_literal(literal_constraint.min_inclusive, literal_constraint.datatype),
                )
            )
        if literal_constraint.max_inclusive is not None:
            graph.add(
                (
                    constraint_resource,
                    URIRef(SH_MAX_INCLUSIVE),
                    _typed_literal(literal_constraint.max_inclusive, literal_constraint.datatype),
                )
            )
        if literal_constraint.min_exclusive is not None:
            graph.add(
                (
                    constraint_resource,
                    URIRef(SH_MIN_EXCLUSIVE),
                    _typed_literal(literal_constraint.min_exclusive, literal_constraint.datatype),
                )
            )
        if literal_constraint.max_exclusive is not None:
            graph.add(
                (
                    constraint_resource,
                    URIRef(SH_MAX_EXCLUSIVE),
                    _typed_literal(literal_constraint.max_exclusive, literal_constraint.datatype),
                )
            )
        if literal_constraint.in_ is not None:
            values = [
                _typed_literal(value, literal_constraint.datatype) for value in literal_constraint.in_
            ]
            graph.add((constraint_resource, URIRef(SH_IN), _make_rdf_list(graph, values)))

    def _add_record_constraints(
        self, parent_resource: Node, property_: RecordProperty, excluded_records: list[Record]
    ) -> list[Node]:
        graph = self.graph
        ret: list[Node] = []
        property_kind_shape = self._make_child_resource(parent_resource, f"{property_.short_code}-kind")
        graph.add((property_kind_shape, URIRef(SH_NODE_KIND), URIRef(SH_BLANK_NODE_OR_IRI)))
        ret.append(property_kind_shape)
        if property_.constraints:
            if (
                property_.nested
                or self.options.validate_reference_types
                or any(constraint.in_ for constraint in property_.constraints)
            ):
                value_resource = self._make_child_resource(parent_resource, f"{property_.short_code}-value")
                ret.append(value_resource)
                if len(property_.constraints) == 1:
                    self._add_record_constraint_properties(
                        value_resource, property_.constraints[0], property_.nested, excluded_records
                    )
                else:
                    children = []
                    for ix, constraint in enumerate(property_.constraints):
                        child = self._make_child_resource(parent_resource, f"{property_.short_code}-value-{ix}")
                        self._add_record_constraint_properties(child, constraint, property_.nested, excluded_records)
                        children.append(child)
                    graph.add((value_resource, URIRef(SH_OR), _make_rdf_list(graph, children)))
        return ret

    def _add_record_constraint_properties(
        self,
        constraint_resource: Node,
        record_constraint: RecordConstraint,
        is_nested: bool,
        excluded_records: list[Record],
    ) -> None:
        if record_constraint.record in excluded_records:
            return
        if is_nested:
            self._add_nested_record_constraint_properties(constraint_resource, record_constraint)
        else:
            self._add_reference_record_constraint_properties(constraint_resource, record_constraint)

    def _add_reference_record_constraint_properties(
        self, constraint_resource: Node, record_constraint: RecordConstraint
    ) -> None:
        graph = self.graph
        if self.options.validate_reference_types:
            graph.add((constraint_resource, URIRef(SH_CLASS), URIRef(record_constraint.record.class_uri)))
        if record_constraint.in_ is not None:
            values = [URIRef(value) for value in record_constraint.in_]
            graph.add((constraint_resource, URIRef(SH_IN), _make_rdf_list(graph, values)))

    def _add_nested_record_constraint_properties(
        self, constraint_resource: Node, record_constraint: RecordConstraint
    ) -> None:
        self.graph.add((constraint_resource, URIRef(SH_SHAPE), URIRef(record_constraint.record.id)))