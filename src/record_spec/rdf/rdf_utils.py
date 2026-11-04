"""RDF literal creation utilities (the Kotlin ``RdfUtils``)."""

from __future__ import annotations

from rdflib import Literal, URIRef


def create_literal(value: str, datatype: str) -> Literal:
    """Create a literal with the given datatype.

    A plain (untyped) literal is created for ``xsd:string`` values, matching
    RDF 1.1's simple-literal semantics.
    """
    if datatype == "http://www.w3.org/2001/XMLSchema#string":
        return Literal(value)
    return Literal(value, datatype=URIRef(datatype))