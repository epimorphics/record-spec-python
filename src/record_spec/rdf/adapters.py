"""Read-side adapters presenting an rdflib graph as a :class:`SchemaAdapter`.

Mirrors the Kotlin ``Jena*Adapter`` classes one-for-one.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from rdflib import RDF, BNode, Literal, URIRef

from record_spec.convert import (
    LiteralConstraintAdapter,
    MixinAdapter,
    PropertyAdapter,
    PropertyMappingAdapter,
    RecordAdapter,
    RecordConstraintAdapter,
    SchemaAdapter,
)
from record_spec.exceptions import RdfParserException
from record_spec.model.property import PropertyKind
from record_spec.model.values import LangString, PrefixMapping
from record_spec.values.curi_resolver import CuriResolver, CuriResolverImpl

from .extensions_helper import ExtensionsHelper
from .vocab import Vocab as V

if TYPE_CHECKING:
    from collections.abc import Iterable

    from rdflib import Graph
    from rdflib.term import Node


def _first_literal(graph: Graph, subject: Node, predicate: str) -> Literal | None:
    """Return the first literal value of ``predicate`` on ``subject``, if any."""
    for obj in graph.objects(subject, URIRef(predicate)):
        if isinstance(obj, Literal):
            return obj
    return None


def _optional_string(graph: Graph, subject: Node, predicate: str) -> str | None:
    lit = _first_literal(graph, subject, predicate)
    return str(lit) if lit is not None else None


def _bool_value(graph: Graph, subject: Node, predicate: str) -> bool:
    lit = _first_literal(graph, subject, predicate)
    return bool(lit.toPython()) if lit is not None else False


def _lang_strings(graph: Graph, subject: Node, predicate: str) -> list[LangString]:
    return [
        LangString(str(lit), lit.language if lit.language else None)
        for lit in (obj for obj in graph.objects(subject, URIRef(predicate)) if isinstance(obj, Literal))
    ]


def _resource_uris(graph: Graph, subject: Node, predicate: str) -> list[str]:
    return [str(obj) for obj in graph.objects(subject, URIRef(predicate)) if isinstance(obj, URIRef)]


def _required_resource(graph: Graph, subject: Node, predicate: str) -> URIRef:
    obj = next((o for o in graph.objects(subject, URIRef(predicate)) if isinstance(o, URIRef)), None)
    if obj is None:
        raise RdfParserException(f"No value found for required property <{predicate}> on resource {subject}")
    return obj


def _required_literal(graph: Graph, subject: Node, predicate: str) -> Literal:
    lit = _first_literal(graph, subject, predicate)
    if lit is None:
        raise RdfParserException(f"No literal value found for required property <{predicate}> on resource {subject}")
    return lit


class RdfAdapterBase:
    """Base class for the RDF adapters (the Kotlin ``JenaAdapterBase``)."""

    def __init__(self, graph: Graph, resource: Node):
        self.graph = graph
        self.resource = resource

    def _lang_strings(self, predicate: str) -> list[LangString]:
        return _lang_strings(self.graph, self.resource, predicate)

    def _resource_uris(self, predicate: str) -> list[str]:
        return _resource_uris(self.graph, self.resource, predicate)

    def _optional_string(self, predicate: str) -> str | None:
        return _optional_string(self.graph, self.resource, predicate)


class RdfDocumentableAdapter(RdfAdapterBase):
    """Documentation properties (label / summary / description) from RDF."""

    @property
    def label(self) -> Iterable[LangString]:
        return self._lang_strings(V.rdfs_label)

    @property
    def summary(self) -> Iterable[LangString]:
        return self._lang_strings(V.rdfs_comment)

    @property
    def description(self) -> Iterable[LangString]:
        return self._lang_strings(V.dct_description)


class RdfExtensibleDocumentableAdapter(RdfDocumentableAdapter):
    """Documentable adapter that also exposes extension records.

    Extension resources (``rec:extension``) are read as JSON trees using
    the combined extension schema; see :class:`ExtensionsHelper`.
    """

    def __init__(self, graph: Graph, resource: Node, extensions_helper: ExtensionsHelper | None = None):
        super().__init__(graph, resource)
        self._extensions_helper = extensions_helper if extensions_helper is not None else ExtensionsHelper()

    @property
    def extensions(self) -> Iterable[dict[str, Any]]:
        from record_spec.rdf.vocab import REC_EXTENSION

        return self._extensions_helper.read_extensions(self.graph, self.resource, REC_EXTENSION)


class RdfPropertyCollectionAdapter(RdfExtensibleDocumentableAdapter, MixinAdapter):
    """A mixin-like collection of properties (the Kotlin ``JenaPropertyCollectionAdapter``)."""

    def __init__(self, graph: Graph, resource: Node, extensions_helper: ExtensionsHelper | None = None):
        super().__init__(graph, resource, extensions_helper)

    @property
    def id(self) -> str:
        return str(self.resource)

    @property
    def properties(self) -> Iterable[PropertyAdapter]:
        return [
            RdfPropertyAdapter(self.graph, obj, self._extensions_helper)
            for obj in self.graph.objects(self.resource, URIRef(V.rec_property))
            if not isinstance(obj, Literal)
        ]


class RdfMixinAdapter(RdfPropertyCollectionAdapter):
    """The RDF adapter for a mixin definition (the Kotlin ``JenaMixinAdapter``)."""


class RdfRecordAdapter(RdfPropertyCollectionAdapter, RecordAdapter):
    """The RDF adapter for a record definition (the Kotlin ``JenaRecordAdapter``)."""

    @property
    def class_uri(self) -> str:
        return str(_required_resource(self.graph, self.resource, V.rec_uri))

    @property
    def short_code(self) -> str:
        return str(_required_literal(self.graph, self.resource, V.rec_short_code))

    @property
    def extends(self) -> str | None:
        extends = self._resource_uris(V.rec_extends)
        return extends[0] if extends else None

    @property
    def mixins(self) -> Iterable[str]:
        return self._resource_uris(V.rec_implements)


class RdfPropertyAdapter(RdfExtensibleDocumentableAdapter, PropertyAdapter):
    """The RDF adapter for a property definition (the Kotlin ``JenaPropertyAdapter``)."""

    def __init__(self, graph: Graph, resource: Node, extensions_helper: ExtensionsHelper | None = None):
        super().__init__(graph, resource, extensions_helper)

    @property
    def short_code(self) -> str:
        return str(_required_literal(self.graph, self.resource, V.rec_short_code))

    @property
    def property_uri(self) -> str:
        return str(_required_resource(self.graph, self.resource, V.rec_uri))

    @property
    def required(self) -> bool:
        return _bool_value(self.graph, self.resource, V.rec_required)

    @property
    def repeatable(self) -> bool:
        return _bool_value(self.graph, self.resource, V.rec_repeatable)

    @property
    def kind(self) -> PropertyKind:
        property_type = next(
            (o for o in self.graph.objects(self.resource, URIRef(RDF.type)) if isinstance(o, URIRef)), None
        )
        if property_type is None:
            raise RdfParserException(
                f"Unable to determine property kind for resource {self.resource}. "
                "An explicit rdf:type statement is required."
            )
        if str(property_type) == V.rec_record_property:
            return PropertyKind.OBJECT
        if str(property_type) == V.rec_literal_property:
            return PropertyKind.LITERAL
        raise RdfParserException(
            f"Unable to determine property kind for resource {self.resource}. "
            f"Unrecognized rdf:type {property_type}."
        )

    @property
    def nested(self) -> bool | None:
        return _bool_value(self.graph, self.resource, V.rec_nested)

    @property
    def reversed(self) -> bool | None:
        return _bool_value(self.graph, self.resource, V.rec_reversed)

    @property
    def literal_constraints(self) -> Iterable[LiteralConstraintAdapter]:
        return [
            RdfLiteralConstraintAdapter(self.graph, constraint)
            for constraint in self._constraint_resources()
            if (constraint, URIRef(V.rec_datatype), None) in self.graph
        ]

    @property
    def record_constraints(self) -> Iterable[RecordConstraintAdapter]:
        return [
            RdfRecordConstraintAdapter(self.graph, constraint)
            for constraint in self._constraint_resources()
            if (constraint, URIRef(V.rec_record_predicate), None) in self.graph
        ]

    @property
    def property_map(self) -> PropertyMappingAdapter | None:
        property_map_resource = next(
            (o for o in self.graph.objects(self.resource, URIRef(V.rec_property_map)) if not isinstance(o, Literal)),
            None,
        )
        if property_map_resource is not None:
            return RdfPropertyMappingAdapter(self.graph, property_map_resource)
        return None

    def _constraint_resources(self) -> list[Node]:
        return [
            obj
            for obj in self.graph.objects(self.resource, URIRef(V.rec_constraint))
            if not isinstance(obj, Literal)
        ]


class RdfLiteralConstraintAdapter(RdfAdapterBase, LiteralConstraintAdapter):
    """The RDF adapter for a literal constraint (the Kotlin ``JenaLiteralConstraintAdapter``)."""

    @property
    def datatype(self) -> str:
        return str(_required_resource(self.graph, self.resource, V.rec_datatype))

    @property
    def pattern(self) -> str | None:
        return self._optional_string(V.rec_pattern)

    @property
    def min_inclusive(self) -> str | None:
        return self._optional_string(V.rec_min_inclusive)

    @property
    def max_inclusive(self) -> str | None:
        return self._optional_string(V.rec_max_inclusive)

    @property
    def min_exclusive(self) -> str | None:
        return self._optional_string(V.rec_min_exclusive)

    @property
    def max_exclusive(self) -> str | None:
        return self._optional_string(V.rec_max_exclusive)

    @property
    def values_in(self) -> list[str] | None:
        values = [
            str(obj) for obj in self.graph.objects(self.resource, URIRef(V.rec_in)) if isinstance(obj, Literal)
        ]
        return values if values else None


class RdfRecordConstraintAdapter(RdfAdapterBase, RecordConstraintAdapter):
    """The RDF adapter for a record constraint (the Kotlin ``JenaRecordConstraintAdapter``)."""

    @property
    def record(self) -> str:
        record_node = next(
            (o for o in self.graph.objects(self.resource, URIRef(V.rec_record_predicate)) if isinstance(o, URIRef)),
            None,
        )
        if record_node is None:
            raise RdfParserException(
                f"Could not find required property <{V.rec_record_predicate}> on resource {self.resource}."
            )
        return str(record_node)

    @property
    def values_in(self) -> list[str] | None:
        values = self._resource_uris(V.rec_in)
        return values if values else None


class RdfPropertyMappingAdapter(RdfAdapterBase, PropertyMappingAdapter):
    """The RDF adapter for a property mapping (the Kotlin ``JenaPropertyMappingAdapter``)."""

    @property
    def key_property(self) -> str:
        lit = _first_literal(self.graph, self.resource, V.rec_key_property)
        if lit is None:
            raise RdfParserException(
                f"Could not find required property <{V.rec_key_property}> on property map resource "
                f"{self.resource}, or property does not have a literal value."
            )
        return str(lit)


class RdfSchemaAdapter(RdfExtensibleDocumentableAdapter, SchemaAdapter, CuriResolver):
    """The RDF adapter for a complete schema (the Kotlin ``JenaSchemaAdapter``)."""

    def __init__(
        self,
        graph: Graph,
        schema_resource: Node,
        base_uri: str | None = None,
        extensions_helper: ExtensionsHelper | None = None,
    ):
        super().__init__(graph, schema_resource, extensions_helper)
        self._base_uri = base_uri
        self._prefixes = [
            PrefixMapping(
                str(_required_literal(graph, pm, V.rec_prefix)),
                str(_required_literal(graph, pm, V.rec_uri)),
            )
            for pm in graph.objects(schema_resource, URIRef(V.rec_prefix_mapping))
            if not isinstance(pm, Literal)
        ]
        self._prefix_curi_resolver = CuriResolverImpl(
            {pm.prefix: pm.uri for pm in self._prefixes},
            base_uri,
        )

    @property
    def identifier(self) -> str | None:
        identifiers = self._resource_uris(V.rec_identifier)
        return identifiers[0] if identifiers else None

    @property
    def base_uri(self) -> str | None:
        return self._base_uri

    @property
    def label(self) -> Iterable[LangString]:
        return self._lang_strings(V.rdfs_label)

    @property
    def summary(self) -> Iterable[LangString]:
        return self._lang_strings(V.rdfs_comment)

    @property
    def description(self) -> Iterable[LangString]:
        return self._lang_strings(V.dct_description)

    @property
    def mixins(self) -> Iterable[MixinAdapter]:
        return [
            RdfMixinAdapter(self.graph, obj, self._extensions_helper)
            for obj in self.graph.objects(self.resource, URIRef(V.rec_mixin))
            if not isinstance(obj, Literal)
        ]

    @property
    def records(self) -> Iterable[RecordAdapter]:
        return [
            RdfRecordAdapter(self.graph, obj, self._extensions_helper)
            for obj in self.graph.objects(self.resource, URIRef(V.rec_record_predicate))
            if not isinstance(obj, Literal)
        ]

    @property
    def prefixes(self) -> Iterable[PrefixMapping]:
        return list(self._prefixes)

    @property
    def imports(self) -> Iterable[str]:
        return self._resource_uris(V.rec_imports)

    def set_base(self, base_uri: str) -> None:
        self._base_uri = base_uri

    def resolve(self, curi: str) -> str:
        return self._prefix_curi_resolver.resolve(curi)

    def compact(self, uri: str) -> str:
        return self._prefix_curi_resolver.compact(uri)


def is_blank_node(node: Node) -> bool:
    return isinstance(node, BNode)