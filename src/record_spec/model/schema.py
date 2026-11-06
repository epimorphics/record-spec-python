"""The Schema: a collection of record and mixin definitions."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING
from urllib.parse import urljoin, urlsplit

from record_spec.convert import MixinAdapter, RecordAdapter, SchemaAdapter
from record_spec.exceptions import (
    MixinExistsException,
    MixinNotFoundException,
    MixinReferencedException,
    RecordClassUriClashException,
    RecordExistsException,
    RecordNotFoundException,
    RecordReferencedException,
    RecordShortCodeClashException,
    SchemaValidationException,
)
from record_spec.model.events import Event, EventListener, RecordModifiedEvent
from record_spec.values.curi_resolver import CuriResolver

from .base import Documentable, Extensible
from .resolvers import MixinResolver, RecordResolver
from .values import LangString, PrefixMapping

if TYPE_CHECKING:
    from collections.abc import Iterable
    from typing import Any

    from record_spec.extensions import ExtensionRecord
    from record_spec.resolver import SchemaResolver

    from .mixin import Mixin
    from .record import Record


class Schema(Documentable, CuriResolver, EventListener, Extensible, RecordResolver, MixinResolver):
    """Represents a collection of record and mixin definitions."""

    #: The base URI used when resolving relative IRI references (see :class:`CuriResolver`).
    base_uri: str | None = None
    #: The IRI identifier of the schema.
    identifier: str | None = None

    def __init__(self) -> None:
        super().__init__()
        self._prefix_mappings: dict[str, str] = {}
        self._mixins: list[Mixin] = []
        self._records: list[Record] = []
        self._requires_validation = False
        self._imports: list[str] = []
        self._extensions: list[ExtensionRecord] = []

    @property
    def adapter(self) -> SchemaAdapter:
        """The read-side adapter over this schema."""
        return Schema.Adapter(self)

    @property
    def requires_validation(self) -> bool:
        """True if changes have been made that require (re)validation."""
        return self._requires_validation

    @property
    def records(self) -> Iterable[Record]:
        """The records defined in this schema."""
        return list(self._records)

    @property
    def mixins(self) -> Iterable[Mixin]:
        """The mixins defined in this schema."""
        return list(self._mixins)

    @property
    def prefix_mappings(self) -> Iterable[PrefixMapping]:
        """The prefix mappings defined by this schema."""
        return [PrefixMapping(prefix, uri) for prefix, uri in self._prefix_mappings.items()]

    @property
    def imports(self) -> Iterable[str]:
        return list(self._imports)

    @property
    def extensions(self) -> Iterable[ExtensionRecord]:
        """The extension records that annotate this schema."""
        return list(self._extensions)

    def set_base(self, base_uri: str) -> None:
        self.base_uri = base_uri

    def create_record(self, record_id: str, uri: str, short_code: str) -> Record:
        """Create a new :class:`Record` and add it to this schema.

        :param record_id: The IRI identifier of the record definition.
        :param uri: The IRI identifier of the RDF class used to type resources
            that conform to this record definition.
        :param short_code: The short-code identifier of the record definition.
        :raises RecordExistsException: if a record with the same id already exists.
        """
        if any(r.id == record_id for r in self._records):
            raise RecordExistsException("id", record_id)
        from .record import Record

        record = Record(self, record_id, uri, short_code)
        self._records.append(record)
        record.add_listener(self)
        self._requires_validation = True
        return record

    def delete_record(self, id_or_short_code: str) -> None:
        """Remove the record with the specified ID or short-code from this schema.

        :raises RecordReferencedException: if the record is currently referenced
            within the schema, either as the parent of another record or in a
            record property constraint (#61 upstream).
        """
        from itertools import chain

        from .property import RecordProperty

        record = self.resolve_record(id_or_short_code)
        if any(r.has_parent(record.id) for r in self._records):
            raise RecordReferencedException(record.id)
        all_properties = chain(
            chain.from_iterable(r.effective_properties for r in self._records),
            chain.from_iterable(m.properties for m in self._mixins),
        )
        if any(
            constraint.record.id == record.id
            for prop in all_properties
            if isinstance(prop, RecordProperty)
            for constraint in prop.constraints
        ):
            raise RecordReferencedException(record.id)
        self._records.remove(record)

    def create_mixin(self, mixin_id: str) -> Mixin:
        """Create a new :class:`Mixin` and add it to this schema.

        :raises MixinExistsException: if a mixin with the same id already exists.
        """
        from .mixin import Mixin

        if any(m.id == mixin_id for m in self._mixins):
            raise MixinExistsException(mixin_id)
        mixin = Mixin(self, mixin_id)
        self._mixins.append(mixin)
        self._requires_validation = True
        return mixin

    def delete_mixin(self, mixin_id: str) -> None:
        """Remove the mixin with the specified ID from this schema.

        :raises MixinReferencedException: if the mixin is referenced by a record.
        """
        mixin = self.resolve_mixin(mixin_id)
        if any(mixin_id in r._mixins for r in self._records):
            raise MixinReferencedException(mixin_id)
        self._mixins.remove(mixin)

    def add_import(self, import_url: str) -> None:
        self._imports.append(import_url)

    def remove_import(self, import_url: str) -> None:
        if import_url in self._imports:
            self._imports.remove(import_url)

    def add_extension_record(self, extension_record: ExtensionRecord) -> None:
        self._extensions.append(extension_record)

    def remove_extension_record(self, extension_record: ExtensionRecord) -> None:
        if extension_record in self._extensions:
            self._extensions.remove(extension_record)

    def resolve_record(self, record_id: str) -> Record:
        """Get the record whose ID is ``record_id`` (full IRI, CURI or short-code
        resolvable against the base)."""
        expanded_id = self.resolve(record_id)
        match = next((r for r in self._records if r.id == expanded_id), None)
        if match is not None:
            return match
        raise RecordNotFoundException(f"No record found with id '{record_id}'")

    def resolve_record_by_class_uri(self, class_uri: str) -> Record:
        expanded_id = self.resolve(class_uri)
        match = next((r for r in self._records if r.class_uri == expanded_id), None)
        if match is not None:
            return match
        raise RecordNotFoundException(f"No record found with classUri '{class_uri}'")

    def resolve_mixin(self, mixin_id: str) -> Mixin:
        """Get the mixin whose ID is ``mixin_id``."""
        expanded_id = self.resolve(mixin_id)
        match = next((m for m in self._mixins if m.id == expanded_id), None)
        if match is not None:
            return match
        raise MixinNotFoundException(f"No mixin found with id '{mixin_id}'")

    def on_event(self, event: Event) -> None:
        if isinstance(event, RecordModifiedEvent):
            self._requires_validation = True

    def validate(self) -> None:
        """Validate this schema.

        :raises SchemaValidationException: if any validation errors are detected;
            the exception carries the individual errors.
        """
        exceptions: list[Exception] = []
        short_code_to_id: dict[str, str] = {}
        for mixin in self._mixins:
            try:
                mixin.validate()
            except Exception as e:  # noqa: BLE001
                exceptions.append(e)
        for record in self._records:
            try:
                record.validate()
                if record.short_code in short_code_to_id and short_code_to_id[record.short_code] != record.id:
                    raise RecordShortCodeClashException(record, short_code_to_id[record.short_code], record.short_code)
                short_code_to_id[record.short_code] = record.id
            except Exception as e:  # noqa: BLE001
                exceptions.append(e)
        for extension in self._extensions:
            try:
                extension.validate(self)
            except Exception as e:  # noqa: BLE001
                exceptions.append(e)
        if exceptions:
            raise SchemaValidationException(exceptions)
        self._requires_validation = False

    def set_prefix_mapping(self, prefix: str, uri: str) -> None:
        self._prefix_mappings[prefix] = uri

    def remove_prefix_mapping(self, prefix: str) -> None:
        self._prefix_mappings.pop(prefix, None)

    def resolve(self, curi: str) -> str:
        """Expand a CURI or relative reference into a full IRI."""
        if ":" in curi:
            prefix, rest = curi.split(":", 1)
            if prefix in self._prefix_mappings:
                return self._prefix_mappings[prefix] + rest
        if urlsplit(curi).scheme:
            return curi
        if self.base_uri is not None:
            return urljoin(self.base_uri, curi)
        raise ValueError(f"URI {curi} is a relative URI and there is no in-scope base URI to resolve against.")

    def compact(self, uri: str) -> str:
        """Compact a full IRI into a CURI or relative reference where possible."""
        split_at = max(uri.rfind("#"), uri.rfind("/"))
        if split_at != -1:
            prefix, suffix = uri[: split_at + 1], uri[split_at + 1 :]
            match = next((pm for pm in self.prefix_mappings if pm.uri == prefix), None)
            if match is not None:
                return f"{match.prefix}:{suffix}"
        if self.base_uri is not None:
            base_dir = urljoin(self.base_uri, ".")
            if uri.startswith(base_dir):
                return uri[len(base_dir) :]
        return uri

    def add(self, schema: Schema) -> None:
        """Merge another schema into this schema (in-place)."""
        self._add_prefix_mappings(schema.prefix_mappings)
        self._add_mixins(schema.mixins)
        self._add_records(schema.records)

    def _add_prefix_mappings(self, prefix_mappings: Iterable[PrefixMapping]) -> None:
        next_prefix_ns = 0
        # Add all prefix mappings.
        # Reassign prefix mappings that clash with an existing prefix string.
        for pm in prefix_mappings:
            if self._prefix_mappings.get(pm.prefix) == pm.uri:
                continue
            prefix = pm.prefix
            while prefix in self._prefix_mappings:
                prefix = "ns" + str(next_prefix_ns)
                next_prefix_ns += 1
            self._prefix_mappings[prefix] = pm.uri

    def _add_mixins(self, mixins: Iterable[Mixin]) -> None:
        from .mixin import merge_mixin

        for mixin in mixins:
            existing = next((m for m in self.mixins if m.id == mixin.id), None)
            if existing is None:
                self._mixins.append(mixin.clone(self))
            else:
                self._mixins.remove(existing)
                self._mixins.append(merge_mixin(self, existing.id, existing, mixin))

    def _add_records(self, records: Iterable[Record]) -> None:
        from .record import merge_record

        to_merge: list[Record] = []
        for record in records:
            existing = next((r for r in self._records if r.id == record.id), None)
            if existing is None:
                self._records.append(record.clone(self))
            else:
                if existing.short_code != record.short_code:
                    raise RecordShortCodeClashException(record, existing.id, existing.short_code)
                if existing.class_uri != record.class_uri:
                    raise RecordClassUriClashException(record, existing.id, existing.class_uri)
                if record.parent_ref is not None:
                    if existing.parent_ref is None:
                        existing.set_parent(record.parent_ref)
                    elif existing.parent_ref != record.parent_ref:
                        from record_spec.exceptions import RecordParentClashException

                        raise RecordParentClashException(existing.id, existing.parent_ref, record.parent_ref)
                to_merge.append(record)
        for record in to_merge:
            existing = next(r for r in self._records if r.id == record.id)
            self._records.remove(existing)
            self._records.append(merge_record(self, existing, record))

    def clone(self) -> Schema:
        """Create a new :class:`Schema` that is a copy of this instance."""
        ret = Schema()
        # NOTE: schema-level documentation is NOT copied by clone, mirroring
        # the upstream Kotlin Schema.clone() (only base URI, imports, prefix
        # mappings, mixins, records and extensions are copied). Record,
        # mixin and property documentation IS preserved via their clones.
        ret.base_uri = self.base_uri
        ret.identifier = self.identifier
        for import_url in self.imports:
            ret.add_import(import_url)
        ret._add_prefix_mappings(self.prefix_mappings)
        for mixin in self.mixins:
            mixin.clone(ret)
        ret._add_records(self.records)
        for ext in self._extensions:
            ret.add_extension_record(ext.clone())
        return ret

    def merge(self, schema: Schema) -> None:
        """Merge another schema into this schema (in-place).

        NOTE: if an exception is raised during processing, this schema may be
        left in a partially updated state.
        """
        self.add(schema)

    def resolve_imports(self, schema_resolver: SchemaResolver) -> Schema:
        """Create a new :class:`Schema` by resolving all imports (including
        transitive imports) of this schema."""
        ret = self.clone()
        ret._resolve_imports(schema_resolver, {ret.base_uri} if ret.base_uri is not None else set())
        return ret

    def _resolve_imports(self, schema_resolver: SchemaResolver, visited: set[str]) -> None:
        if not any(True for _ in self.imports):
            return
        for import_url in list(self.imports):
            if import_url not in visited:
                schema_to_import = schema_resolver.resolve(import_url)
                schema_to_import._resolve_imports(schema_resolver, visited | {import_url})
                self.add(schema_to_import)
            self.remove_import(import_url)

    class Adapter(SchemaAdapter):
        """The read-side adapter for a schema."""

        def __init__(self, model: Schema):
            self.model = model

        @property
        def identifier(self) -> str | None:
            return self.model.identifier

        @property
        def base_uri(self) -> str | None:
            return self.model.base_uri

        @property
        def label(self) -> Iterable[LangString]:
            return self.model.label

        @property
        def summary(self) -> Iterable[LangString]:
            return self.model.summary

        @property
        def description(self) -> Iterable[LangString]:
            return self.model.description

        @property
        def mixins(self) -> Iterable[MixinAdapter]:
            from .mixin import Mixin

            result: list[MixinAdapter] = []
            for m in self.model.mixins:
                assert isinstance(m, Mixin)
                result.append(Mixin.Adapter(m))
            return result

        @property
        def records(self) -> Iterable[RecordAdapter]:
            from .record import Record

            result: list[RecordAdapter] = []
            for r in self.model.records:
                assert isinstance(r, Record)
                result.append(Record.Adapter(r))
            return result

        @property
        def prefixes(self) -> Iterable[PrefixMapping]:
            return self.model.prefix_mappings

        @property
        def imports(self) -> Iterable[str]:
            return self.model.imports

        @property
        def extensions(self) -> Iterable[dict[str, Any]]:
            from record_spec.extensions import to_tree_with_type

            return [to_tree_with_type(ext) for ext in self.model._extensions]


#: The pattern that all short-codes must match.
SHORT_CODE_REGEX = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*")