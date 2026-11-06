"""Writes JSON trees (record instances) as RDF per a record definition.

The rdflib-based equivalent of the Kotlin ``RdfRecordWriter``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from rdflib import RDF, BNode, URIRef
from rdflib.term import Literal, Node

from record_spec.exceptions import RdfRecordWriterException
from record_spec.jsonschema import JsonOptions
from record_spec.model.constraints import LiteralConstraint
from record_spec.model.property import LiteralProperty, Property, RecordProperty
from record_spec.values.datatypes import RDF_LANG_STRING, XSD

if TYPE_CHECKING:
    from rdflib import Graph

    from record_spec.model import Record


def _create_literal(value: str, datatype: str | None) -> Literal:
    """Create a literal with the given datatype (the Kotlin
    ``RdfRecordWriter.createLiteral``): a plain literal for ``xsd:string``
    and null datatypes."""
    if datatype is None or datatype == XSD + "string":
        return Literal(value)
    return Literal(value, datatype=URIRef(datatype))


class RdfRecordWriter:
    """Writes JSON trees as RDF resources per a :class:`Record` definition.

    :param graph: The RDF graph to write into.
    :param json_options: The JSON property-name options (id/type/value/
        language properties, bare reference ids).
    """

    def __init__(self, graph: Graph, json_options: JsonOptions | None = None):
        self.graph = graph
        self.options = json_options if json_options is not None else JsonOptions()

    def write_record(self, tree: dict[str, Any], record: Record) -> Node:
        """Write a JSON tree as an RDF resource typed per ``record``.

        :return: The resource written (a URI or blank node).
        """
        id_value = tree.get(self.options.id_property)
        if isinstance(id_value, str):
            resource: Node = URIRef(id_value)
        else:
            resource = BNode()
        self.graph.add((resource, RDF.type, URIRef(record.class_uri)))
        for prop in record.effective_properties:
            if prop.short_code in tree:
                self._write_property_value(prop, tree[prop.short_code], resource)
        return resource

    def _write_property_value(self, prop: Property, value: Any, resource: Node) -> None:
        if value is None:
            if prop.required:
                raise RdfRecordWriterException(
                    f"Unable to serialize null value for required property {prop.short_code} ({prop.property_uri})"
                )
            return
        if isinstance(value, list):
            for item in value:
                self._write_property_value(prop, item, resource)
            return
        if isinstance(prop, LiteralProperty):
            self._write_literal_property_value(prop, value, resource)
        elif isinstance(prop, RecordProperty):
            self._write_record_property_value(prop, value, resource)
        else:
            raise ValueError(f"Unsupported property type: {type(prop)!r}")

    def _write_literal_property_value(self, prop: LiteralProperty, value: Any, resource: Node) -> None:
        value_property = self.options.value_property
        language_property = self.options.language_property
        literal: Literal | None = None
        if isinstance(value, bool) and prop.accepts(XSD + "boolean"):
            literal = Literal(value)
        elif (
            isinstance(value, int) and not isinstance(value, bool) and prop.accepts(XSD + "integer")
        ):
            literal = _create_literal(str(value), XSD + "integer")
        elif isinstance(value, float) and prop.accepts(XSD + "double"):
            # Typed from the parsed value (mirrors Jena createTypedLiteral(double))
            literal = Literal(float(value))
        elif isinstance(value, float) and prop.accepts(XSD + "float"):
            # Typed from the lexical form (mirrors Jena createLiteral(text, xsd:float))
            literal = _create_literal(str(value), XSD + "float")
        elif (
            isinstance(value, dict)
            and value_property in value
            and self.options.type_property in value
            and isinstance(value[self.options.type_property], str)
            and prop.accepts(value[self.options.type_property])
        ):
            literal = _create_literal(str(value[value_property]), value[self.options.type_property])
        elif (
            isinstance(value, dict)
            and value_property in value
            and language_property in value
            and prop.accepts(RDF_LANG_STRING)
        ):
            literal = Literal(str(value[value_property]), lang=str(value[language_property]))
        elif isinstance(value, dict) and value_property in value and prop.accepts(XSD + "string"):
            literal = _create_literal(str(value[value_property]), None)
        elif isinstance(value, str) and prop.accepts(XSD + "string"):
            literal = _create_literal(value, None)
        elif len(prop.constraints) == 1:
            constraint: LiteralConstraint = prop.constraints[0]
            literal = _create_literal(str(value), constraint.datatype)
        else:
            raise RdfRecordWriterException(
                f"Could not find an appropriate value constraint that accepts the JSON value "
                f"{value} on property {prop.short_code} ({prop.property_uri})"
            )
        if literal is None:
            raise RdfRecordWriterException(
                f"Literal creation failed for value {value} on property {prop.short_code} ({prop.property_uri})"
            )
        self.graph.add((resource, URIRef(prop.property_uri), literal))

    def _write_record_property_value(self, prop: RecordProperty, value: Any, resource: Node) -> None:
        target = self._get_record_property_value(prop, value)
        self.graph.add((resource, URIRef(prop.property_uri), target))

    def _get_record_property_value(self, prop: RecordProperty, value: Any) -> Node:
        if prop.nested:
            # Nested property
            if not isinstance(value, dict):
                raise RdfRecordWriterException(
                    f"Could not write value {value} for property {prop.short_code} ({prop.property_uri}). "
                    f"Expected an object with a {self.options.type_property} property."
                )
            id_value = value.get(self.options.id_property)
            target: Node = URIRef(id_value) if isinstance(id_value, str) else BNode()
            if len(prop.constraints) == 1:
                return self.write_record(value, prop.constraints[0].record)
            type_value = value.get(self.options.type_property)
            if not isinstance(type_value, str):
                raise RdfRecordWriterException(
                    f"Could not write value {value} for property {prop.short_code} ({prop.property_uri}): "
                    f"Required property {self.options.type_property} was not found."
                )
            for constraint in prop.constraints:
                if constraint.record.class_uri == type_value:
                    return self.write_record(value, constraint.record)
            return target
        # Reference property
        if self.options.bare_reference_ids:
            if isinstance(value, str):
                # Interpret the node value as the referenced record's IRI
                return URIRef(value)
            raise RdfRecordWriterException(
                f"Encountered an unexpected value {value} for property {prop.short_code} ({prop.property_uri}). "
                "Expected a string value."
            )
        # Expect an object with an id property
        if isinstance(value, dict) and self.options.id_property in value:
            id_value = value[self.options.id_property]
            if isinstance(id_value, str):
                return URIRef(id_value)
        raise RdfRecordWriterException(
            f"Could not write value {value} for property {prop.short_code} ({prop.property_uri}). "
            f"Expected an object with a {self.options.id_property} property."
        )