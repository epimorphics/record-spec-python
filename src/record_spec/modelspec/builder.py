"""Build a model-spec definition from a record-spec schema.

The Python equivalent of the Kotlin upstream ``modelspec/ModelSpecBuilder.kt``.
"""

from __future__ import annotations

import re
from dataclasses import replace
from typing import TYPE_CHECKING

import yaml

from record_spec.model.base import Documentable
from record_spec.model.property import LiteralProperty, Property, PropertyKind, RecordProperty
from record_spec.modelspec.model_def import ClassDef, ModelDef, PropertyDef, PropertyType
from record_spec.modelspec.options import ModelSpecOptions

if TYPE_CHECKING:
    from collections.abc import Iterable

    from record_spec.model.mixin import Mixin
    from record_spec.model.record import Record
    from record_spec.model.schema import Schema

_RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
_RDFS_RESOURCE = "http://www.w3.org/2000/01/rdf-schema#Resource"

# The standard prefix mappings that are merged with the schema's own prefixes
# on output, mirroring Jena's ``PrefixMapping.Standard`` (used by the upstream
# Kotlin builder).
_STANDARD_PREFIXES: dict[str, str] = {
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "dc": "http://purl.org/dc/elements/1.1/",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "owl": "http://www.w3.org/2002/07/owl#",
}

# Matches the maximal trailing substring of a URI that is a legal XML name,
# mirroring Jena's ``SplitIRI.splitXML`` split point: the longest legal name
# that runs to the end of the URI, starting at a name-start character.
_TRAILING_XML_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_.\-]*$")


class ModelSpecBuilder:
    """Builds a model-spec definition (:class:`ModelDef`) from a record-spec
    :class:`~record_spec.model.Schema`, and serializes it as model-spec YAML.

    The mapping rules replicate the record-spec conversion in the model-spec
    repository (``com.epimorphics.modelspec.recordspec``), so that output from
    this builder is directly comparable with output from that tool:

    - records (and, if ``ModelSpecOptions.include_mixins`` is set, mixins) become classes
    - ``short_code`` becomes the class name, ``class_uri`` the class URI
    - ``extends`` becomes ``sub_class_of``, plus the record's mixin identifiers
      when mixins are included
    - a class is ``polymorphic`` if any other record extends it
    - object properties take their range class URIs as types, literal properties
      their datatype constraints
    - a synthetic ``rdf:type`` property, named per ``ModelSpecOptions.type_property``,
      is added to every class
    - the preferred (English) description becomes the comment
    """

    def __init__(self, options: ModelSpecOptions | None = None) -> None:
        self._options = options if options is not None else ModelSpecOptions()

    def build(self, schema: Schema) -> ModelDef:
        """Build a model-spec definition from a record-spec schema.

        :param schema: the schema to convert
        :return: the model-spec definition
        """
        return ModelDef(
            prefixes=self._prefix_mapping(schema),
            classes=self._classes(schema),
            comment=_preferred_description(schema),
        )

    def write_yaml(self, schema: Schema) -> str:
        """Build a model-spec definition from a record-spec schema and serialize
        it as model-spec YAML, with URIs compacted using the schema's prefixes.

        :param schema: the schema to convert
        :return: the model-spec YAML document
        """
        prefixes = self._prefix_mapping(schema)
        model_def = _compact(self.build(schema), prefixes)
        return yaml.safe_dump(model_def.to_dict(), sort_keys=False)

    def _classes(self, schema: Schema) -> list[ClassDef]:
        records = [self._build_record(schema, record) for record in schema.records]
        mixins = [self._build_mixin(mixin) for mixin in schema.mixins] if self._options.include_mixins else []
        return sorted([*records, *mixins], key=lambda cls: cls.uri)

    def _build_record(self, schema: Schema, record: Record) -> ClassDef:
        return ClassDef(
            uri=record.class_uri,
            name=record.short_code,
            sub_class_of=self._super_classes(record),
            properties=self._properties(schema, record.effective_properties),
            comment=_preferred_description(record),
            polymorphic=bool(record.all_descendents()),
        )

    def _build_mixin(self, mixin: Mixin) -> ClassDef:
        return ClassDef(
            uri=mixin.id,
            name=_local_name(mixin.id),
            sub_class_of=[],
            properties=self._mixin_properties(mixin),
            comment=_preferred_description(mixin),
            polymorphic=False,
        )

    def _super_classes(self, record: Record) -> list[str]:
        parents = [record.parent.class_uri] if record.parent is not None else []
        if self._options.include_mixins:
            return [*parents, *(mixin.id for mixin in record.mixins)]
        return parents

    def _properties(self, schema: Schema | None, props: Iterable[Property]) -> list[PropertyDef]:
        return sorted(
            [self._build_property(schema, prop) for prop in props] + [self._rdf_type_property()],
            key=lambda prop: prop.uri,
        )

    def _mixin_properties(self, mixin: Mixin) -> list[PropertyDef]:
        return sorted(
            [self._build_property(None, prop) for prop in mixin.properties] + [self._rdf_type_property()],
            key=lambda prop: prop.uri,
        )

    def _build_property(self, schema: Schema | None, prop: Property) -> PropertyDef:
        types = self._types(schema, prop)
        return PropertyDef(
            uri=prop.property_uri,
            name=prop.short_code,
            kind=PropertyType.OBJECT if prop.kind is PropertyKind.OBJECT else PropertyType.DATATYPE,
            types=types if types else None,
            optional=not prop.required,
            multi=prop.repeatable,
            unique=False,
            comment=_preferred_description(prop),
        )

    def _types(self, schema: Schema | None, prop: Property) -> list[str]:
        if isinstance(prop, RecordProperty):
            return [record.class_uri for record in prop.range]
        if isinstance(prop, LiteralProperty):
            if schema is None:
                return list(prop.range)
            return [schema.resolve(datatype) for datatype in prop.range]
        return []

    def _rdf_type_property(self) -> PropertyDef:
        return PropertyDef(
            uri=_RDF_TYPE,
            name=self._options.type_property,
            kind=None,
            types=[_RDFS_RESOURCE],
            optional=True,
            multi=True,
            unique=False,
            comment=None,
        )

    def _prefix_mapping(self, schema: Schema) -> dict[str, str]:
        prefixes = dict(_STANDARD_PREFIXES)
        for mapping in schema.prefix_mappings:
            prefixes[mapping.prefix] = mapping.uri
        return prefixes


def _compact(model_def: ModelDef, prefixes: dict[str, str]) -> ModelDef:
    return replace(
        model_def,
        classes=[_compact_class(cls, prefixes) for cls in model_def.classes],
    )


def _compact_class(cls: ClassDef, prefixes: dict[str, str]) -> ClassDef:
    return replace(
        cls,
        uri=_qname_for(cls.uri, prefixes) or cls.uri,
        sub_class_of=[_qname_for(uri, prefixes) or uri for uri in cls.sub_class_of]
        if cls.sub_class_of is not None
        else None,
        properties=[_compact_property(prop, prefixes) for prop in cls.properties],
    )


def _compact_property(prop: PropertyDef, prefixes: dict[str, str]) -> PropertyDef:
    return replace(
        prop,
        uri=_qname_for(prop.uri, prefixes) or prop.uri,
        types=[_qname_for(uri, prefixes) or uri for uri in prop.types] if prop.types is not None else None,
        value_base=_qname_for(prop.value_base, prefixes) or prop.value_base
        if prop.value_base is not None
        else None,
    )


def _qname_for(uri: str, prefixes: dict[str, str]) -> str | None:
    """Return the qname for ``uri`` (``prefix:localName``), or None if no prefix
    maps to a namespace covering ``uri``, mirroring Jena's ``qnameFor``."""
    match = _TRAILING_XML_NAME.search(uri)
    if match is None:
        return None
    namespace = uri[: match.start()]
    prefix = next((p for p, ns in prefixes.items() if ns == namespace), None)
    return f"{prefix}:{uri[match.start() :]}" if prefix is not None else None


def _local_name(uri: str) -> str:
    """The local (last path or fragment) portion of a URI, as used for the name
    of a mixin-derived class."""
    match = _TRAILING_XML_NAME.search(uri)
    return uri[match.start() :] if match is not None else uri


def _preferred_description(documentable: Documentable) -> str | None:
    """The preferred description of a documentable model element: the English
    description if present, then the untagged description, then the first
    description. Where several descriptions share a language, the last wins."""
    descriptions_by_language = {ls.language: ls.value for ls in documentable.description}
    if descriptions_by_language.get("en") is not None:
        return descriptions_by_language["en"]
    if descriptions_by_language.get(None) is not None:
        return descriptions_by_language[None]
    return next((ls.value for ls in documentable.description), None)
