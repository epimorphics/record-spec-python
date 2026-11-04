"""Builds a :class:`Schema` from a :class:`SchemaAdapter` (any source format)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from urllib.parse import urljoin

from record_spec.extensions import UnrecognizedExtensionRecord, get_extension_service

from .base import Extensible, PropertyFactory
from .property import PropertyKind
from .property_mapping import PropertyMapping
from .schema import Schema

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
    from record_spec.extensions import ExtensionRecord

    from .mixin import Mixin
    from .property import LiteralProperty, RecordProperty
    from .record import Record


class SchemaBuilder:
    """Builds a :class:`Schema` from a :class:`SchemaAdapter`.

    The build is two-phase: all record stubs are created first so that
    forward references (records used before they are declared) resolve.
    """

    def build(self, adapter: SchemaAdapter, source_uri: str | None = None, validate: bool = True) -> Schema:
        schema = Schema()
        schema.identifier = adapter.identifier
        base_uri = adapter.base_uri if adapter.base_uri is not None else source_uri
        if base_uri is not None:
            schema.set_base(base_uri)
        for prefix_mapping in adapter.prefixes:
            schema.set_prefix_mapping(prefix_mapping.prefix, prefix_mapping.uri)
        schema.label.extend(adapter.label)
        schema.summary.extend(adapter.summary)
        schema.description.extend(adapter.description)
        stub_records = [
            (record_adapter, self._build_stub(schema, record_adapter)) for record_adapter in adapter.records
        ]
        for mixin_adapter in adapter.mixins:
            self._build_mixin(schema, mixin_adapter)
        for stub in stub_records:
            self._build_record(stub)
        base = schema.base_uri
        for import_path in adapter.imports:
            import_url = urljoin(base, import_path) if base is not None else import_path
            schema.add_import(import_url)
        self._add_extensions(list(adapter.extensions), schema)
        if validate:
            schema.validate()
        return schema

    @staticmethod
    def _extension_type(extension_node: dict[str, Any]) -> str | None:
        value = extension_node.get("@type")
        if value is None:
            value = extension_node.get("type")
        return value if isinstance(value, str) else None

    def _add_extensions(self, extension_defs: Iterable[dict[str, Any]], target: Extensible) -> None:
        for extension_record in self._deserialize_extensions(extension_defs):
            target.add_extension_record(extension_record)

    def _deserialize_extensions(self, extensions: Iterable[dict[str, Any]]) -> list[ExtensionRecord]:
        result: list[ExtensionRecord] = []
        for ext in extensions:
            extension_type = self._extension_type(ext)
            if extension_type is not None:
                service = get_extension_service(extension_type)
                if service is not None:
                    result.append(service.tree_to_record(ext))
                else:
                    result.append(UnrecognizedExtensionRecord(extension_type, ext))
        return result

    def _build_stub(self, schema: Schema, adapter: RecordAdapter) -> Record:
        return schema.create_record(adapter.id, adapter.class_uri, adapter.short_code)

    def _build_mixin(self, schema: Schema, adapter: MixinAdapter) -> Mixin:
        mixin = schema.create_mixin(adapter.id)
        for prop_adapter in adapter.properties:
            self._build_property(mixin, prop_adapter)
        mixin.label.extend(adapter.label)
        mixin.summary.extend(adapter.summary)
        mixin.description.extend(adapter.description)
        self._add_extensions(list(adapter.extensions), mixin)
        return mixin

    def _build_record(self, stub: tuple[RecordAdapter, Record]) -> Record:
        record_adapter, record = stub
        record.label.extend(record_adapter.label)
        record.summary.extend(record_adapter.summary)
        record.description.extend(record_adapter.description)
        for mixin_id in record_adapter.mixins:
            record.add_mixin(mixin_id)
        record.set_parent(record_adapter.extends)
        for prop_adapter in record_adapter.properties:
            self._build_property(record, prop_adapter)
        self._add_extensions(list(record_adapter.extensions), record)
        return record

    def _build_property(
        self, property_factory: PropertyFactory, adapter: PropertyAdapter
    ) -> LiteralProperty | RecordProperty:
        if adapter.kind == PropertyKind.LITERAL:
            lit = property_factory.create_literal_property(
                adapter.short_code,
                adapter.property_uri,
                adapter.required,
                adapter.repeatable,
            )
            for constraint_adapter in adapter.literal_constraints:
                self._build_literal_constraint(lit, constraint_adapter)
            lit.label.extend(adapter.label)
            lit.summary.extend(adapter.summary)
            lit.description.extend(adapter.description)
            self._add_extensions(list(adapter.extensions), lit)
            return lit
        rec = property_factory.create_record_property(
            adapter.short_code,
            adapter.property_uri,
            adapter.required,
            adapter.repeatable,
            adapter.nested if adapter.nested is not None else False,
            adapter.reversed if adapter.reversed is not None else False,
        )
        if adapter.property_map is not None:
            rec.set_property_map(self._build_property_map(adapter.property_map))
        for rec_constraint_adapter in adapter.record_constraints:
            self._build_record_constraint(rec, rec_constraint_adapter)
        rec.label.extend(adapter.label)
        rec.summary.extend(adapter.summary)
        rec.description.extend(adapter.description)
        self._add_extensions(list(adapter.extensions), rec)
        return rec

    @staticmethod
    def _build_property_map(adapter: PropertyMappingAdapter) -> PropertyMapping:
        return PropertyMapping(adapter.key_property)

    @staticmethod
    def _build_literal_constraint(prop: LiteralProperty, adapter: LiteralConstraintAdapter) -> None:
        prop.add_constraint(
            adapter.datatype,
            adapter.pattern,
            adapter.min_inclusive,
            adapter.max_inclusive,
            adapter.min_exclusive,
            adapter.max_exclusive,
            list(adapter.values_in) if adapter.values_in is not None else None,
        )

    @staticmethod
    def _build_record_constraint(prop: RecordProperty, adapter: RecordConstraintAdapter) -> None:
        values_in = list(adapter.values_in) if adapter.values_in is not None else None
        prop.add_constraint(adapter.record, values_in)