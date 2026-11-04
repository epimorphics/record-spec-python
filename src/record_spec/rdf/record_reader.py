"""Reads RDF resources as JSON trees per a record definition.

The rdflib-based equivalent of the Kotlin ``RdfRecordReader``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from rdflib import RDF, URIRef
from rdflib.term import BNode, Literal, Node

from record_spec.exceptions import (
    RdfRecordReaderException,
    RecordNotFoundException,
)
from record_spec.model.constraints import RecordConstraint
from record_spec.model.property import LiteralProperty, Property, RecordProperty
from record_spec.values.datatypes import RDF_LANG_STRING, XSD

if TYPE_CHECKING:
    from collections.abc import Iterable

    from rdflib import Graph

    from record_spec.model import Record
    from record_spec.model.resolvers import RecordResolver


def _datatype_uri(literal: Literal) -> str | None:
    """Return the RDF 1.1 datatype IRI of a literal.

    RDF 1.1: a plain literal is an ``xsd:string``-typed literal, and a
    language-tagged literal is an ``rdf:langString``-typed literal; rdflib
    represents both with a ``None`` datatype, so normalize.
    """
    if literal.language is not None:
        return RDF_LANG_STRING
    if literal.datatype is not None:
        return str(literal.datatype)
    return XSD + "string"


class RdfRecordReader:
    """Reads RDF resources as JSON trees (record instances) per a
    :class:`Record` definition.

    :param graph: The RDF graph to read from.
    :param record_resolver: The resolver used to look up record definitions
        by class URI when a nested resource's type must be inferred.
    """

    def __init__(self, graph: Graph, record_resolver: RecordResolver):
        self.graph = graph
        self.record_resolver = record_resolver

    def read_value(self, resource: Node, record: Record) -> dict[str, Any]:
        """Read an RDF resource as an instance of the specified record
        definition.

        :param resource: The RDF resource that is the root of the record
            to read.
        :param record: The schema record definition.
        :return: The record as a JSON-compatible tree.
        """
        result: dict[str, Any] = {}
        if isinstance(resource, URIRef):
            result["@id"] = str(resource)
        result["@type"] = record.class_uri
        for prop in record.effective_properties:
            value = self._read_property_value(resource, prop)
            if value is not None:
                result[prop.short_code] = value
        return result

    def _read_property_value(self, resource: Node, prop: Property) -> Any:
        if isinstance(prop, LiteralProperty):
            return self._read_literal_property_value(resource, prop)
        if isinstance(prop, RecordProperty):
            return self._read_record_property_value(resource, prop)
        raise ValueError(f"Unsupported property type: {type(prop)!r}")

    def _read_literal_property_value(self, resource: Node, prop: LiteralProperty) -> Any:
        literals = [obj for obj in self.graph.objects(resource, URIRef(prop.property_uri)) if isinstance(obj, Literal)]
        self._validate_cardinality(prop, literals)
        if not literals:
            return None
        nodes = [self._make_literal_value(literal) for literal in literals if self._is_valid_literal(literal, prop)]
        return self._wrap_property_value(prop, nodes)

    def _read_record_property_value(self, resource: Node, prop: RecordProperty) -> Any:
        resources = [
            obj for obj in self.graph.objects(resource, URIRef(prop.property_uri)) if isinstance(obj, (URIRef, BNode))
        ]
        self._validate_cardinality(prop, resources)
        if not resources:
            return None
        nodes = [
            self._make_record_value(r, prop, self._match_constraint(r, prop)) for r in resources
        ]
        nodes = [node for node in nodes if node is not None]
        return self._wrap_property_value(prop, nodes)

    @staticmethod
    def _validate_cardinality(prop: Property, resource_list: list[Any]) -> None:
        if not resource_list and prop.required:
            raise RdfRecordReaderException(
                f"No value found for required property {prop.property_uri} ({prop.short_code})."
            )
        if len(resource_list) > 1 and not prop.repeatable:
            raise RdfRecordReaderException(
                f"Too many values found for non-repeatable property {prop.property_uri} ({prop.short_code})."
            )

    def _is_valid_literal(self, literal: Literal, prop: LiteralProperty) -> bool:
        datatype = _datatype_uri(literal)
        return not prop.constraints or any(constraint.datatype == datatype for constraint in prop.constraints)

    def _match_constraint(self, resource: Node, prop: RecordProperty) -> RecordConstraint | None:
        types = [str(obj) for obj in self.graph.objects(resource, RDF.type) if isinstance(obj, URIRef)]
        return next(
            (
                constraint
                for constraint in prop.constraints
                if constraint.record.class_uri in types
                and (constraint.in_ is None or str(resource) in constraint.in_)
            ),
            None,
        )

    @staticmethod
    def _make_literal_value(literal: Literal) -> Any:
        datatype = _datatype_uri(literal)
        if datatype == XSD + "string":
            return str(literal)
        if datatype == XSD + "integer":
            return int(str(literal))
        if datatype == XSD + "float":
            return float(str(literal))
        if datatype == XSD + "double":
            return float(str(literal))
        if datatype == XSD + "boolean":
            return str(literal).strip().lower() == "true" or str(literal).strip() == "1"
        result: dict[str, Any] = {"@value": str(literal)}
        if literal.language is not None and str(literal.language):
            result["@language"] = str(literal.language)
        else:
            result["@type"] = datatype
        return result

    def _make_record_value(
        self, resource: Node, prop: RecordProperty, constraint: RecordConstraint | None
    ) -> dict[str, Any] | None:
        if prop.nested:
            if constraint is not None:
                return self.read_value(resource, constraint.record)
            resource_type = next(
                (obj for obj in self.graph.objects(resource, RDF.type) if isinstance(obj, URIRef)), None
            )
            if resource_type is None:
                raise RdfRecordReaderException(
                    f"Unable to read resource {resource} as it has no rdf:type and the type cannot be "
                    f"inferred from the property {prop.property_uri} ({prop.short_code})."
                )
            try:
                record = self.record_resolver.resolve_record_by_class_uri(str(resource_type))
            except RecordNotFoundException:
                raise RdfRecordReaderException(
                    f"Unable to read resource {resource} as it has an rdf:type ({resource_type}) "
                    "which does not map to any known record definition."
                ) from None
            return self.read_value(resource, record)
        return {"@id": str(resource)}

    def _wrap_property_value(self, prop: Property, json_values: list[Any]) -> Any:
        if prop.repeatable:
            return json_values
        return json_values[0]

    def read_extensions(self, resource: Node, extension_property: str) -> Iterable[dict[str, Any]]:
        """Read the extension records attached to a resource via the given
        extension predicate, using the combined extension schema."""
        from record_spec.rdf.extensions_helper import ExtensionsHelper

        helper = ExtensionsHelper()
        result: list[dict[str, Any]] = []
        for ext_resource in (
            obj for obj in self.graph.objects(resource, URIRef(extension_property)) if not isinstance(obj, Literal)
        ):
            tree = helper.read_extension(self.graph, ext_resource)
            if tree is not None:
                result.append(tree)
        return result