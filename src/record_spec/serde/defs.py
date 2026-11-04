"""The YAML/JSON def-tree: the serialization form of a schema.

Each ``*Def`` class mirrors its Kotlin counterpart in the ``serde`` package.
``from_dict`` implements what Jackson's deserialization does (including
ignoring unknown properties and the ``kind`` discriminator for properties);
``to_dict`` implements the serialization (omitting empty values, mirroring
Jackson's ``JsonInclude.NON_EMPTY``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Union

from record_spec.convert import (
    LiteralConstraintAdapter,
    MixinAdapter,
    PropertyMappingAdapter,
    RecordAdapter,
    RecordConstraintAdapter,
    SchemaAdapter,
)
from record_spec.model.property import PropertyKind
from record_spec.model.values import LangString, PrefixMapping
from record_spec.values.curi_resolver import CuriResolver, CuriResolverImpl

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping


__all__ = [
    "LangStringDef",
    "PrefixMappingDef",
    "PropertyMappingDef",
    "LiteralConstraintDef",
    "RecordConstraintDef",
    "PropertyDef",
    "LiteralPropertyDef",
    "RecordPropertyDef",
    "MixinDef",
    "RecordDef",
    "SchemaDef",
    "AnyPropertyDef",
    "expand_type",
    "compact_type",
]


class LangStringDef:
    """A language-tagged string in the def-tree: either a plain string or ``{value, language}``."""

    def __init__(self, value: str, language: str | None = None):
        self.value = value
        self.language = language

    @classmethod
    def from_dict(cls, data: Any) -> LangStringDef:
        if isinstance(data, str):
            return cls(data)
        if isinstance(data, dict) and "value" in data:
            language = data.get("language")
            return cls(data["value"], language if isinstance(language, str) else None)
        raise ValueError(f"Expected a string or an object with a 'value' property, got: {data!r}")

    def to_dict(self) -> dict[str, str] | str:
        if self.language is None:
            return self.value
        return {"value": self.value, "language": self.language}

    def __repr__(self) -> str:
        return f"LangStringDef(value={self.value!r}, language={self.language!r})"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, LangStringDef) and self.value == other.value and self.language == other.language


def _lang_strings(data: Any) -> list[LangStringDef] | None:
    if data is None:
        return None
    return [LangStringDef.from_dict(item) for item in data]


def _as_str(value: Any) -> str | None:
    """Coerce a scalar YAML/JSON value to str (Jackson coerces numbers into String fields)."""
    if value is None:
        return None
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _extensions(data: Any) -> list[dict[str, Any]] | None:
    """Implement the ExtensionsDeserializer: a JSON array of objects, otherwise null."""
    if isinstance(data, list):
        return [dict(item) for item in data if isinstance(item, dict)]
    return None


class PrefixMappingDef:
    def __init__(self, prefix: str, uri: str):
        self.prefix = prefix
        self.uri = uri

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> PrefixMappingDef:
        return cls(data["prefix"], data["uri"])

    def to_dict(self) -> dict[str, str]:
        return {"prefix": self.prefix, "uri": self.uri}


class PropertyMappingDef:
    def __init__(self, key_property: str):
        self.key_property = key_property

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> PropertyMappingDef:
        return cls(data["keyProperty"])

    def to_dict(self) -> dict[str, str]:
        return {"keyProperty": self.key_property}

    class Adapter(PropertyMappingAdapter):
        def __init__(self, model: PropertyMappingDef):
            self.model = model

        @property
        def key_property(self) -> str:
            return self.model.key_property


class LiteralConstraintDef:
    def __init__(
        self,
        datatype: str,
        pattern: str | None = None,
        min_inclusive: str | None = None,
        max_inclusive: str | None = None,
        min_exclusive: str | None = None,
        max_exclusive: str | None = None,
        in_: list[str] | None = None,
    ):
        self.datatype = datatype
        self.pattern = pattern
        self.min_inclusive = min_inclusive
        self.max_inclusive = max_inclusive
        self.min_exclusive = min_exclusive
        self.max_exclusive = max_exclusive
        self.in_ = in_

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> LiteralConstraintDef:
        in_ = data.get("in")
        return cls(
            data["datatype"],
            _as_str(data.get("pattern")),
            _as_str(data.get("minInclusive")),
            _as_str(data.get("maxInclusive")),
            _as_str(data.get("minExclusive")),
            _as_str(data.get("maxExclusive")),
            [_as_str(v) or "" for v in in_] if in_ is not None else None,
        )

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"datatype": self.datatype}
        for key, value in (
            ("pattern", self.pattern),
            ("minInclusive", self.min_inclusive),
            ("maxInclusive", self.max_inclusive),
            ("minExclusive", self.min_exclusive),
            ("maxExclusive", self.max_exclusive),
            ("in", self.in_),
        ):
            if value is not None and value != []:
                result[key] = value
        return result

    class Adapter(LiteralConstraintAdapter):
        def __init__(self, curi_resolver: CuriResolver, constraint_def: LiteralConstraintDef):
            self._curi_resolver = curi_resolver
            self.model = constraint_def

        @property
        def datatype(self) -> str:
            return self._curi_resolver.resolve(self.model.datatype)

        @property
        def pattern(self) -> str | None:
            return self.model.pattern

        @property
        def min_inclusive(self) -> str | None:
            return self.model.min_inclusive

        @property
        def max_inclusive(self) -> str | None:
            return self.model.max_inclusive

        @property
        def min_exclusive(self) -> str | None:
            return self.model.min_exclusive

        @property
        def max_exclusive(self) -> str | None:
            return self.model.max_exclusive

        @property
        def values_in(self) -> list[str] | None:
            return self.model.in_


class RecordConstraintDef:
    def __init__(self, record: str, in_: list[str] | None = None):
        self.record = record
        self.in_ = in_

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> RecordConstraintDef:
        in_ = data.get("in")
        return cls(data["record"], [str(v) for v in in_] if in_ is not None else None)

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"record": self.record}
        if self.in_:
            result["in"] = self.in_
        return result

    class Adapter(RecordConstraintAdapter):
        def __init__(self, curi_resolver: CuriResolver, constraint_def: RecordConstraintDef):
            self._curi_resolver = curi_resolver
            self.model = constraint_def

        @property
        def record(self) -> str:
            return self._curi_resolver.resolve(self.model.record) if ":" in self.model.record else self.model.record

        @property
        def values_in(self) -> list[str] | None:
            if self.model.in_ is None:
                return None
            return [self._curi_resolver.resolve(v) if ":" in v else v for v in self.model.in_]


class PropertyDef:
    """Base class for the two kinds of property definitions."""

    def __init__(
        self,
        property_uri: str,
        label: list[LangStringDef] | None,
        summary: list[LangStringDef] | None,
        description: list[LangStringDef] | None,
        required: bool | None,
        repeatable: bool | None,
        kind: PropertyKind,
        extensions: list[dict[str, Any]] | None,
    ):
        self.property_uri = property_uri
        self.label = label
        self.summary = summary
        self.description = description
        self.required = required
        self.repeatable = repeatable
        self.kind = kind
        self.extensions = extensions

    def _to_dict_common(self) -> dict[str, Any]:
        result: dict[str, Any] = {"propertyUri": self.property_uri}
        for key, value in (
            ("label", self.label),
            ("summary", self.summary),
            ("description", self.description),
        ):
            if value:
                result[key] = [item.to_dict() for item in value]
        if self.required is not None:
            result["required"] = self.required
        if self.repeatable is not None:
            result["repeatable"] = self.repeatable
        if self.extensions:
            result["extensions"] = self.extensions
        return result

    @staticmethod
    def _from_dict_common(data: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "propertyUri": data["propertyUri"],
            "label": _lang_strings(data.get("label")),
            "summary": _lang_strings(data.get("summary")),
            "description": _lang_strings(data.get("description")),
            "required": data.get("required"),
            "repeatable": data.get("repeatable"),
            "extensions": _extensions(data.get("extensions")),
        }


class LiteralPropertyDef(PropertyDef):
    def __init__(
        self,
        property_uri: str,
        label: list[LangStringDef] | None,
        summary: list[LangStringDef] | None,
        description: list[LangStringDef] | None,
        required: bool | None,
        repeatable: bool | None,
        constraints: list[LiteralConstraintDef] | None,
        extensions: list[dict[str, Any]] | None,
    ):
        super().__init__(
            property_uri, label, summary, description, required, repeatable, PropertyKind.LITERAL, extensions
        )
        self.constraints = constraints

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> LiteralPropertyDef:
        common = cls._from_dict_common(data)
        constraints = data.get("constraints")
        return cls(
            common["propertyUri"],
            common["label"],
            common["summary"],
            common["description"],
            common["required"],
            common["repeatable"],
            [LiteralConstraintDef.from_dict(c) for c in constraints] if constraints is not None else None,
            common["extensions"],
        )

    def to_dict(self) -> dict[str, Any]:
        result = self._to_dict_common()
        result["kind"] = "literal"
        if self.constraints:
            result["constraints"] = [c.to_dict() for c in self.constraints]
        return result

    class Adapter:
        """The read-side adapter for a literal property definition."""

        def __init__(self, curi_resolver: CuriResolver, property_short_code: str, property_def: LiteralPropertyDef):
            self._curi_resolver = curi_resolver
            self.short_code = property_short_code
            self.model = property_def

        @property
        def property_uri(self) -> str:
            return self._curi_resolver.resolve(self.model.property_uri)

        @property
        def label(self) -> Iterable[LangString]:
            return [LangString(item.value, item.language) for item in self.model.label or []]

        @property
        def summary(self) -> Iterable[LangString]:
            return [LangString(item.value, item.language) for item in self.model.summary or []]

        @property
        def description(self) -> Iterable[LangString]:
            return [LangString(item.value, item.language) for item in self.model.description or []]

        @property
        def required(self) -> bool:
            return self.model.required if self.model.required is not None else False

        @property
        def repeatable(self) -> bool:
            return self.model.repeatable if self.model.repeatable is not None else False

        @property
        def kind(self) -> PropertyKind:
            return PropertyKind.LITERAL

        @property
        def nested(self) -> bool | None:
            return None

        @property
        def reversed(self) -> bool | None:
            return None

        @property
        def literal_constraints(self) -> Iterable[LiteralConstraintAdapter]:
            return [LiteralConstraintDef.Adapter(self._curi_resolver, c) for c in self.model.constraints or []]

        @property
        def record_constraints(self) -> list[RecordConstraintAdapter]:
            return []

        @property
        def property_map(self) -> PropertyMappingAdapter | None:
            return None

        @property
        def extensions(self) -> Iterable[dict[str, Any]]:
            return [expand_type(dict(ext), self._curi_resolver) for ext in self.model.extensions or []]


class RecordPropertyDef(PropertyDef):
    def __init__(
        self,
        property_uri: str,
        label: list[LangStringDef] | None,
        summary: list[LangStringDef] | None,
        description: list[LangStringDef] | None,
        required: bool | None,
        repeatable: bool | None,
        nested: bool | None,
        reversed: bool | None,
        constraints: list[RecordConstraintDef] | None,
        map_: PropertyMappingDef | None,
        extensions: list[dict[str, Any]] | None,
    ):
        super().__init__(
            property_uri, label, summary, description, required, repeatable, PropertyKind.OBJECT, extensions
        )
        self.nested = nested
        self.reversed = reversed
        self.constraints = constraints
        self.map = map_

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> RecordPropertyDef:
        common = cls._from_dict_common(data)
        constraints = data.get("constraints")
        map_ = data.get("map")
        return cls(
            common["propertyUri"],
            common["label"],
            common["summary"],
            common["description"],
            common["required"],
            common["repeatable"],
            data.get("nested"),
            data.get("reversed"),
            [RecordConstraintDef.from_dict(c) for c in constraints] if constraints is not None else None,
            PropertyMappingDef.from_dict(map_) if map_ is not None else None,
            common["extensions"],
        )

    def to_dict(self) -> dict[str, Any]:
        result = self._to_dict_common()
        result["kind"] = "object"
        if self.nested is not None:
            result["nested"] = self.nested
        if self.reversed is not None:
            result["reversed"] = self.reversed
        if self.constraints:
            result["constraints"] = [c.to_dict() for c in self.constraints]
        if self.map is not None:
            result["map"] = self.map.to_dict()
        return result

    class Adapter:
        """The read-side adapter for a record property definition."""

        def __init__(self, curi_resolver: CuriResolver, property_short_code: str, property_def: RecordPropertyDef):
            self._curi_resolver = curi_resolver
            self.short_code = property_short_code
            self.model = property_def

        @property
        def property_uri(self) -> str:
            return self._curi_resolver.resolve(self.model.property_uri)

        @property
        def label(self) -> Iterable[LangString]:
            return [LangString(item.value, item.language) for item in self.model.label or []]

        @property
        def summary(self) -> Iterable[LangString]:
            return [LangString(item.value, item.language) for item in self.model.summary or []]

        @property
        def description(self) -> Iterable[LangString]:
            return [LangString(item.value, item.language) for item in self.model.description or []]

        @property
        def required(self) -> bool:
            return self.model.required if self.model.required is not None else False

        @property
        def repeatable(self) -> bool:
            return self.model.repeatable if self.model.repeatable is not None else False

        @property
        def kind(self) -> PropertyKind:
            return PropertyKind.OBJECT

        @property
        def nested(self) -> bool | None:
            return self.model.nested if self.model.nested is not None else False

        @property
        def reversed(self) -> bool | None:
            return self.model.reversed if self.model.reversed is not None else False

        @property
        def literal_constraints(self) -> list[LiteralConstraintAdapter]:
            return []

        @property
        def record_constraints(self) -> Iterable[RecordConstraintAdapter]:
            return [RecordConstraintDef.Adapter(self._curi_resolver, c) for c in self.model.constraints or []]

        @property
        def property_map(self) -> PropertyMappingAdapter | None:
            return PropertyMappingDef.Adapter(self.model.map) if self.model.map is not None else None

        @property
        def extensions(self) -> Iterable[dict[str, Any]]:
            return [expand_type(dict(ext), self._curi_resolver) for ext in self.model.extensions or []]


AnyPropertyDef = Union["LiteralPropertyDef", "RecordPropertyDef"]


def property_def_from_dict(data: Mapping[str, Any]) -> AnyPropertyDef:
    """Dispatch on the ``kind`` discriminator (Jackson's ``@JsonTypeInfo``)."""
    kind = data.get("kind")
    if kind == "literal":
        return LiteralPropertyDef.from_dict(data)
    if kind == "object":
        return RecordPropertyDef.from_dict(data)
    raise ValueError(f"Unsupported property kind: {kind!r}")


class MixinDef:
    def __init__(
        self,
        label: list[LangStringDef] | None,
        summary: list[LangStringDef] | None,
        description: list[LangStringDef] | None,
        properties: dict[str, AnyPropertyDef] | None,
        extensions: list[dict[str, Any]] | None,
    ):
        self.label = label
        self.summary = summary
        self.description = description
        self.properties = properties
        self.extensions = extensions

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> MixinDef:
        properties = data.get("properties")
        return cls(
            _lang_strings(data.get("label")),
            _lang_strings(data.get("summary")),
            _lang_strings(data.get("description")),
            {key: property_def_from_dict(value) for key, value in properties.items()}
            if properties is not None
            else None,
            _extensions(data.get("extensions")),
        )

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        if self.label:
            result["label"] = [item.to_dict() for item in self.label]
        if self.summary:
            result["summary"] = [item.to_dict() for item in self.summary]
        if self.description:
            result["description"] = [item.to_dict() for item in self.description]
        if self.properties:
            result["properties"] = {key: value.to_dict() for key, value in self.properties.items()}
        if self.extensions:
            result["extensions"] = self.extensions
        return result

    class Adapter(MixinAdapter):
        def __init__(self, curi_resolver: CuriResolver, mixin_id: str, mixin_def: MixinDef):
            self._curi_resolver = curi_resolver
            self._id = self._curi_resolver.resolve(mixin_id)
            self.model = mixin_def

        @property
        def id(self) -> str:
            return self._id

        @property
        def label(self) -> Iterable[LangString]:
            return [LangString(item.value, item.language) for item in self.model.label or []]

        @property
        def summary(self) -> Iterable[LangString]:
            return [LangString(item.value, item.language) for item in self.model.summary or []]

        @property
        def description(self) -> Iterable[LangString]:
            return [LangString(item.value, item.language) for item in self.model.description or []]

        @property
        def properties(self) -> Iterable[Any]:
            result: list[Any] = []
            for short_code, prop_def in (self.model.properties or {}).items():
                if isinstance(prop_def, LiteralPropertyDef):
                    result.append(LiteralPropertyDef.Adapter(self._curi_resolver, short_code, prop_def))
                elif isinstance(prop_def, RecordPropertyDef):
                    result.append(RecordPropertyDef.Adapter(self._curi_resolver, short_code, prop_def))
                else:
                    raise ValueError(f"Unsupported property definition type: {type(prop_def)!r}")
            return result

        @property
        def extensions(self) -> Iterable[dict[str, Any]]:
            return [expand_type(dict(ext), self._curi_resolver) for ext in self.model.extensions or []]


class RecordDef:
    def __init__(
        self,
        class_uri: str,
        short_code: str,
        label: list[LangStringDef] | None,
        summary: list[LangStringDef] | None,
        description: list[LangStringDef] | None,
        mixins: list[str] | None,
        extends: str | None,
        properties: dict[str, AnyPropertyDef] | None,
        extensions: list[dict[str, Any]] | None,
    ):
        self.class_uri = class_uri
        self.short_code = short_code
        self.label = label
        self.summary = summary
        self.description = description
        self.mixins = mixins
        self.extends = extends
        self.properties = properties
        self.extensions = extensions

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> RecordDef:
        properties = data.get("properties")
        mixins = data.get("mixins")
        return cls(
            data["classUri"],
            data["shortCode"],
            _lang_strings(data.get("label")),
            _lang_strings(data.get("summary")),
            _lang_strings(data.get("description")),
            list(mixins) if mixins is not None else None,
            data.get("extends"),
            {key: property_def_from_dict(value) for key, value in properties.items()}
            if properties is not None
            else None,
            _extensions(data.get("extensions")),
        )

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "classUri": self.class_uri,
            "shortCode": self.short_code,
        }
        if self.label:
            result["label"] = [item.to_dict() for item in self.label]
        if self.summary:
            result["summary"] = [item.to_dict() for item in self.summary]
        if self.description:
            result["description"] = [item.to_dict() for item in self.description]
        if self.mixins:
            result["mixins"] = self.mixins
        if self.extends is not None:
            result["extends"] = self.extends
        if self.properties:
            result["properties"] = {key: value.to_dict() for key, value in self.properties.items()}
        if self.extensions:
            result["extensions"] = self.extensions
        return result

    class Adapter(RecordAdapter):
        def __init__(self, curi_resolver: CuriResolver, record_id: str, record_def: RecordDef):
            self._curi_resolver = curi_resolver
            self._id = self._curi_resolver.resolve(record_id)
            self.model = record_def

        @property
        def id(self) -> str:
            return self._id

        @property
        def class_uri(self) -> str:
            return self._curi_resolver.resolve(self.model.class_uri)

        @property
        def short_code(self) -> str:
            return self.model.short_code

        @property
        def label(self) -> Iterable[LangString]:
            return [LangString(item.value, item.language) for item in self.model.label or []]

        @property
        def summary(self) -> Iterable[LangString]:
            return [LangString(item.value, item.language) for item in self.model.summary or []]

        @property
        def description(self) -> Iterable[LangString]:
            return [LangString(item.value, item.language) for item in self.model.description or []]

        @property
        def extends(self) -> str | None:
            return self.model.extends

        @property
        def mixins(self) -> Iterable[str]:
            return list(self.model.mixins or [])

        @property
        def properties(self) -> Iterable[Any]:
            result: list[Any] = []
            for short_code, prop_def in (self.model.properties or {}).items():
                if isinstance(prop_def, LiteralPropertyDef):
                    result.append(LiteralPropertyDef.Adapter(self._curi_resolver, short_code, prop_def))
                elif isinstance(prop_def, RecordPropertyDef):
                    result.append(RecordPropertyDef.Adapter(self._curi_resolver, short_code, prop_def))
                else:
                    raise ValueError(f"Unsupported property definition type: {type(prop_def)!r}")
            return result

        @property
        def extensions(self) -> Iterable[dict[str, Any]]:
            return [expand_type(dict(ext), self._curi_resolver) for ext in self.model.extensions or []]


class SchemaDef:
    """The def-tree of a complete schema."""

    def __init__(
        self,
        identifier: str | None = None,
        base: str | None = None,
        imports: list[str] | None = None,
        prefixes: list[PrefixMappingDef] | None = None,
        label: list[LangStringDef] | None = None,
        summary: list[LangStringDef] | None = None,
        description: list[LangStringDef] | None = None,
        mixins: dict[str, MixinDef] | None = None,
        records: dict[str, RecordDef] | None = None,
        extensions: list[dict[str, Any]] | None = None,
    ):
        self.identifier = identifier
        self.base = base
        self.imports = imports
        self.prefixes = prefixes
        self.label = label
        self.summary = summary
        self.description = description
        self.mixins = mixins
        self.records = records
        self.extensions = extensions

    @classmethod
    def from_dict(cls, data: Any) -> SchemaDef:
        if not isinstance(data, dict):
            raise ValueError(f"Expected a schema object, got: {type(data)!r}")
        imports = data.get("imports")
        prefixes = data.get("prefixes")
        mixins = data.get("mixins")
        records = data.get("records")
        return cls(
            identifier=data.get("identifier"),
            base=data.get("base"),
            imports=list(imports) if imports is not None else None,
            prefixes=[PrefixMappingDef.from_dict(p) for p in prefixes] if prefixes is not None else None,
            label=_lang_strings(data.get("label")),
            summary=_lang_strings(data.get("summary")),
            description=_lang_strings(data.get("description")),
            mixins={key: MixinDef.from_dict(value) for key, value in mixins.items()}
            if mixins is not None
            else None,
            records={key: RecordDef.from_dict(value) for key, value in records.items()}
            if records is not None
            else None,
            extensions=_extensions(data.get("extensions")),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dict, omitting null and empty values (NON_EMPTY)."""
        result: dict[str, Any] = {}
        if self.identifier is not None:
            result["identifier"] = self.identifier
        if self.base is not None:
            result["base"] = self.base
        if self.imports:
            result["imports"] = self.imports
        if self.prefixes:
            result["prefixes"] = [p.to_dict() for p in self.prefixes]
        if self.label:
            result["label"] = [item.to_dict() for item in self.label]
        if self.summary:
            result["summary"] = [item.to_dict() for item in self.summary]
        if self.description:
            result["description"] = [item.to_dict() for item in self.description]
        if self.mixins:
            result["mixins"] = {key: value.to_dict() for key, value in self.mixins.items()}
        if self.records:
            result["records"] = {key: value.to_dict() for key, value in self.records.items()}
        if self.extensions:
            result["extensions"] = self.extensions
        return result

    @property
    def adapter(self) -> SchemaAdapter:
        return SchemaDef.Adapter(self)

    class Adapter(SchemaAdapter):
        def __init__(self, schema_def: SchemaDef):
            self.schema = schema_def
            self._curi_resolver = CuriResolverImpl(
                {p.prefix: p.uri for p in schema_def.prefixes} if schema_def.prefixes else {},
                schema_def.base,
            )

        @property
        def identifier(self) -> str | None:
            return self.schema.identifier

        @property
        def base_uri(self) -> str | None:
            return self.schema.base

        @property
        def imports(self) -> Iterable[str]:
            return list(self.schema.imports or [])

        @property
        def prefixes(self) -> Iterable[PrefixMapping]:
            return [PrefixMapping(p.prefix, p.uri) for p in self.schema.prefixes or []]

        @property
        def label(self) -> Iterable[LangString]:
            return [LangString(item.value, item.language) for item in self.schema.label or []]

        @property
        def summary(self) -> Iterable[LangString]:
            return [LangString(item.value, item.language) for item in self.schema.summary or []]

        @property
        def description(self) -> Iterable[LangString]:
            return [LangString(item.value, item.language) for item in self.schema.description or []]

        @property
        def mixins(self) -> Iterable[MixinAdapter]:
            return [
                MixinDef.Adapter(self._curi_resolver, key, value)
                for key, value in (self.schema.mixins or {}).items()
            ]

        @property
        def records(self) -> Iterable[RecordAdapter]:
            return [
                RecordDef.Adapter(self._curi_resolver, key, value)
                for key, value in (self.schema.records or {}).items()
            ]

        @property
        def extensions(self) -> Iterable[dict[str, Any]]:
            return [expand_type(dict(ext), self._curi_resolver) for ext in self.schema.extensions or []]


def expand_type(extension_node: dict[str, Any], curi_resolver: CuriResolver) -> dict[str, Any]:
    """Expand the type of an extension node (``@type`` or ``type``) in place."""
    if "@type" in extension_node:
        extension_node["@type"] = curi_resolver.resolve(extension_node["@type"])
    elif "type" in extension_node:
        extension_node["type"] = curi_resolver.resolve(extension_node["type"])
    return extension_node


def compact_type(extension_node: dict[str, Any], curi_resolver: CuriResolver) -> dict[str, Any]:
    """Compact the type of an extension node (``@type`` or ``type``) in place."""
    if "@type" in extension_node:
        extension_node["@type"] = curi_resolver.compact(extension_node["@type"])
    elif "type" in extension_node:
        extension_node["type"] = curi_resolver.compact(extension_node["type"])
    return extension_node