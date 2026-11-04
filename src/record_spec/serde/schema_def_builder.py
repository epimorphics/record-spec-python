"""Builds a :class:`SchemaDef` (the YAML/JSON def-tree) from a :class:`SchemaAdapter`."""

from __future__ import annotations

from typing import TYPE_CHECKING

from record_spec.model import LangString, PropertyKind

from .defs import (
    AnyPropertyDef,
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
    compact_type,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

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


class SchemaDefBuilder:
    """Builds a :class:`SchemaDef` from any :class:`SchemaAdapter`.

    All URIs in the resulting def-tree are compacted against the adapter's
    prefix mappings; namespaces without a prefix are assigned generated
    ``ns<N>`` prefixes.
    """

    def __init__(self) -> None:
        self._prefix_ix = 0
        self._reverse_prefix_mappings: dict[str, str] = {}

    def build(self, adapter: SchemaAdapter) -> SchemaDef:
        from record_spec.values.curi_resolver import CuriResolverImpl

        curi_resolver: CuriResolver = CuriResolverImpl(
            {pm.prefix: pm.uri for pm in adapter.prefixes},
            adapter.base_uri,
        )
        prefix_mappings = [PrefixMappingDef(pm.prefix, pm.uri) for pm in adapter.prefixes]
        for pm in adapter.prefixes:
            self._reverse_prefix_mappings.setdefault(pm.uri, pm.prefix)
        mixins = {
            curi_resolver.compact(mixin_adapter.id): self._build_mixin(mixin_adapter, curi_resolver)
            for mixin_adapter in adapter.mixins
        }
        records = {
            curi_resolver.compact(record_adapter.id): self._build_record(record_adapter, curi_resolver)
            for record_adapter in adapter.records
        }
        extensions = [compact_type(dict(ext), curi_resolver) for ext in adapter.extensions]
        return SchemaDef(
            identifier=adapter.identifier,
            base=curi_resolver.base_uri,
            imports=list(adapter.imports) if any(True for _ in adapter.imports) else None,
            prefixes=prefix_mappings,
            label=self._make_lang_string_def_list(adapter.label),
            summary=self._make_lang_string_def_list(adapter.summary),
            description=self._make_lang_string_def_list(adapter.description),
            mixins=mixins or None,
            records=records or None,
            extensions=extensions or None,
        )

    def _build_mixin(self, adapter: MixinAdapter, curi_resolver: CuriResolver) -> MixinDef:
        properties = list(adapter.properties)
        return MixinDef(
            label=self._make_lang_string_def_list(adapter.label),
            summary=self._make_lang_string_def_list(adapter.summary),
            description=self._make_lang_string_def_list(adapter.description),
            properties=(
                {
                    prop_adapter.short_code: self._build_property(prop_adapter, curi_resolver)
                    for prop_adapter in properties
                }
                if properties
                else None
            ),
            extensions=(
                [compact_type(dict(ext), curi_resolver) for ext in adapter.extensions]
                if any(True for _ in adapter.extensions)
                else None
            ),
        )

    def _build_record(self, adapter: RecordAdapter, curi_resolver: CuriResolver) -> RecordDef:
        properties = list(adapter.properties)
        return RecordDef(
            class_uri=self._make_prefix_mapping(adapter.class_uri, curi_resolver),
            short_code=adapter.short_code,
            label=self._make_lang_string_def_list(adapter.label),
            summary=self._make_lang_string_def_list(adapter.summary),
            description=self._make_lang_string_def_list(adapter.description),
            mixins=(
                [curi_resolver.compact(m) for m in adapter.mixins] if any(True for _ in adapter.mixins) else None
            ),
            extends=curi_resolver.compact(adapter.extends) if adapter.extends is not None else None,
            properties=(
                {
                    prop_adapter.short_code: self._build_property(prop_adapter, curi_resolver)
                    for prop_adapter in properties
                }
                if properties
                else None
            ),
            extensions=(
                [compact_type(dict(ext), curi_resolver) for ext in adapter.extensions]
                if any(True for _ in adapter.extensions)
                else None
            ),
        )

    def _build_property(self, adapter: PropertyAdapter, curi_resolver: CuriResolver) -> AnyPropertyDef:
        if adapter.kind == PropertyKind.LITERAL:
            literal_constraints = list(adapter.literal_constraints)
            return LiteralPropertyDef(
                property_uri=self._make_prefix_mapping(adapter.property_uri, curi_resolver),
                label=self._make_lang_string_def_list(adapter.label),
                summary=self._make_lang_string_def_list(adapter.summary),
                description=self._make_lang_string_def_list(adapter.description),
                required=adapter.required,
                repeatable=adapter.repeatable,
                constraints=(
                    [self._build_literal_constraint(c, curi_resolver) for c in literal_constraints]
                    if literal_constraints
                    else None
                ),
                extensions=[compact_type(dict(ext), curi_resolver) for ext in adapter.extensions],
            )
        record_constraints = list(adapter.record_constraints)
        extensions = list(adapter.extensions)
        return RecordPropertyDef(
            property_uri=self._make_prefix_mapping(adapter.property_uri, curi_resolver),
            label=self._make_lang_string_def_list(adapter.label),
            summary=self._make_lang_string_def_list(adapter.summary),
            description=self._make_lang_string_def_list(adapter.description),
            required=adapter.required,
            repeatable=adapter.repeatable,
            nested=adapter.nested,
            reversed=adapter.reversed,
            constraints=(
                [self._build_record_constraint(c, curi_resolver) for c in record_constraints]
                if record_constraints
                else None
            ),
            map_=self._build_property_map(adapter.property_map) if adapter.property_map is not None else None,
            extensions=[compact_type(dict(ext), curi_resolver) for ext in extensions],
        )

    @staticmethod
    def _build_property_map(adapter: PropertyMappingAdapter) -> PropertyMappingDef:
        return PropertyMappingDef(adapter.key_property)

    def _build_literal_constraint(
        self, adapter: LiteralConstraintAdapter, curi_resolver: CuriResolver
    ) -> LiteralConstraintDef:
        values_in = list(adapter.values_in) if adapter.values_in is not None else None
        return LiteralConstraintDef(
            datatype=self._make_prefix_mapping(adapter.datatype, curi_resolver),
            pattern=adapter.pattern,
            min_inclusive=adapter.min_inclusive,
            max_inclusive=adapter.max_inclusive,
            min_exclusive=adapter.min_exclusive,
            max_exclusive=adapter.max_exclusive,
            in_=values_in,
        )

    @staticmethod
    def _build_record_constraint(adapter: RecordConstraintAdapter, curi_resolver: CuriResolver) -> RecordConstraintDef:
        values_in = list(adapter.values_in) if adapter.values_in is not None else None
        return RecordConstraintDef(
            record=curi_resolver.compact(adapter.record),
            in_=values_in,
        )

    @staticmethod
    def _make_lang_string_def_list(lang_strings: Iterable[LangString]) -> list[LangStringDef] | None:
        items = [LangStringDef(ls.value, ls.language) for ls in lang_strings]
        return items if items else None

    def _make_prefix_mapping(self, uri_string: str, curi_resolver: CuriResolver) -> str:
        split_at = max(uri_string.rfind("#"), uri_string.rfind("/"))
        if split_at != -1:
            prefix, suffix = uri_string[: split_at + 1], uri_string[split_at + 1 :]
            if prefix in self._reverse_prefix_mappings:
                return f"{self._reverse_prefix_mappings[prefix]}:{suffix}"
            new_prefix = f"ns{self._prefix_ix}"
            self._prefix_ix += 1
            self._reverse_prefix_mappings[prefix] = new_prefix
            return f"{new_prefix}:{suffix}"
        return uri_string