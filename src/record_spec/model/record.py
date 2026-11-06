"""Record definitions: the heart of the record-spec model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from record_spec.convert import PropertyAdapter, RecordAdapter
from record_spec.exceptions import (
    CircularInheritanceException,
    IncompatiblePropertyException,
    PropertyUriExistsException,
    ShortCodeExistsException,
    InvalidRecordException,
    InvalidShortCodeException,
    MixinExistsException,
    MixinNotFoundException,
    MixinPropertyClashException,
    RecordSpecException,
)
from record_spec.model.events import (
    Event,
    EventListener,
    EventSourceMixin,
    MixinModifiedEvent,
    PropertyModifiedEvent,
    RecordModifiedEvent,
)

from .base import Documentable, Extensible, PropertyFactory
from .property import LiteralProperty, RecordProperty
from .property_helper import PropertyHelper
from .values import LangString

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator
    from typing import Any

    from record_spec.extensions import ExtensionRecord

    from .mixin import Mixin
    from .property import Property
    from .property_mapping import PropertyMapping
    from .schema import Schema


class Record(Documentable, Extensible, EventListener, EventSourceMixin, PropertyFactory):
    """Represents a single record definition."""

    def __init__(self, schema: Schema, record_id: str, class_uri: str, short_code: str):
        super().__init__()
        self._init_listeners()
        self._schema = schema
        self.id = record_id
        self.class_uri = class_uri
        self.short_code = short_code
        self._parent_ref: str | None = None
        self._modified = True
        # Ordered set of mixin ids (mirrors Kotlin's LinkedHashSet).
        self._mixins: dict[str, None] = {}
        self._direct_properties: list[Property] = []
        self._effective_properties: list[Property] = []
        self._extensions: list[ExtensionRecord] = []

    @property
    def compact_id(self) -> str:
        return self._schema.compact(self.id)

    @property
    def parent(self) -> Record | None:
        """The record definition that this definition inherits from, if any."""
        return self._schema.resolve_record(self._parent_ref) if self._parent_ref is not None else None

    @property
    def parent_ref(self) -> str | None:
        """The (resolved) id of the parent record definition, if any."""
        return self._parent_ref

    @property
    def effective_properties(self) -> Iterable[Property]:
        """All properties allowed on this record, including those inherited from
        its :attr:`parent` and those contributed by any mixins."""
        if self._modified:
            self._update_effective_properties()
        return list(self._effective_properties)

    @property
    def mixins(self) -> list[Mixin]:
        """The mixins directly specified on this record.

        NOTE: a record may also include mixins inherited from its :attr:`parent`;
        those mixins are NOT returned by this property.
        """
        return [self._schema.resolve_mixin(mixin_id) for mixin_id in self._mixins]

    @property
    def extensions(self) -> Iterable[ExtensionRecord]:
        from itertools import chain

        return list(chain(*(mixin.extensions for mixin in self.mixins))) + list(self._extensions)

    def clone(self, schema: Schema) -> Record:
        """Create a copy of this record belonging to ``schema``."""
        from .property import clone_property

        clone = Record(schema, self.id, self.class_uri, self.short_code)
        clone.set_parent(self._parent_ref)
        for mixin_id in self._mixins:
            clone.add_mixin(mixin_id)
        for prop in self._direct_properties:
            clone_property(clone, prop)
        for ext in self._extensions:
            clone.add_extension_record(ext.clone())
        # Documentation is copied by clone (#58 upstream).
        clone.label.extend(LangString(ls.value, ls.language) for ls in self.label)
        clone.summary.extend(LangString(ls.value, ls.language) for ls in self.summary)
        clone.description.extend(LangString(ls.value, ls.language) for ls in self.description)
        return clone

    def set_parent(self, super_class_ref: str | None) -> None:
        """Set the parent record definition that this record inherits from.

        Pass None to remove any existing inheritance relationship.

        :param super_class_ref: The short-code or ID of the parent record definition.
        """
        resolved_super_class_ref = self._schema.resolve(super_class_ref) if super_class_ref is not None else None
        if self._parent_ref != resolved_super_class_ref:
            self._parent_ref = resolved_super_class_ref
            self._on_changed()

    def create_record_property(
        self,
        short_code: str,
        uri: str,
        required: bool = False,
        repeatable: bool = False,
        nested: bool = False,
        reversed: bool = False,
        property_mapping: PropertyMapping | None = None,
    ) -> RecordProperty:
        """Create a :class:`RecordProperty` and add it to the properties directly
        defined on this record.

        :raises ShortCodeExistsException: if another property with the same
            short code is already defined on this record.
        :raises PropertyUriExistsException: if another property with the same
            predicate URI is already defined on this record.
        """
        self._check_property_clash(short_code, uri)
        p = RecordProperty(
            self._schema, short_code, uri, required, repeatable, nested, reversed, property_mapping
        )
        self._direct_properties.append(p)
        p.add_listener(self)
        self._on_changed()
        return p

    def create_literal_property(
        self,
        short_code: str,
        uri: str,
        required: bool = False,
        repeatable: bool = False,
    ) -> LiteralProperty:
        """Create a :class:`LiteralProperty` and add it to the properties directly
        defined on this record.

        :raises ShortCodeExistsException: if another property with the same
            short code is already defined on this record.
        :raises PropertyUriExistsException: if another property with the same
            predicate URI is already defined on this record.
        """
        self._check_property_clash(short_code, uri)
        p = LiteralProperty(short_code, uri, required, repeatable)
        self._direct_properties.append(p)
        p.add_listener(self)
        self._on_changed()
        return p

    def _check_property_clash(self, short_code: str, uri: str) -> None:
        """Creation-time clash checking against directly-defined properties
        (#60 upstream). Only catches clashes with properties defined directly
        on the same record; inherited clashes are handled by schema validation."""
        if any(prop.short_code == short_code for prop in self._direct_properties):
            raise ShortCodeExistsException(short_code)
        if any(prop.property_uri == uri for prop in self._direct_properties):
            raise PropertyUriExistsException(uri)

    def remove_property(self, prop: Property | str) -> None:
        """Remove the specified property (by short-code or instance) from the
        properties directly defined on this record.

        If no matching property exists, this method returns without modifying the record.
        """
        if isinstance(prop, str):
            prop_short_code = prop
            match = next((p for p in self._direct_properties if p.short_code == prop_short_code), None)
            if match is not None:
                self._direct_properties.remove(match)
                self._on_changed()
            return
        if prop in self._direct_properties:
            self._direct_properties.remove(prop)
            self._on_changed()

    def add_mixin(self, mixin_id: str) -> None:
        """Add a mixin to the list of mixins defined on this record.

        :param mixin_id: The short-code or IRI identifier of the mixin to add.
        :raises MixinExistsException: if the record already has a mixin with an
            ID or short-code that matches ``mixin_id``.
        :raises MixinNotFoundException: if no mixin with the specified ID or
            short-code could be found in the parent schema.
        """
        self._mixins[mixin_id] = None
        self._on_changed()

    def remove_mixin(self, mixin_id: str) -> None:
        """Remove the mixin with the specified ID or short-code from this record.

        If no matching mixin exists in the list of mixins directly defined on
        this record, this method returns without modifying the record.
        """
        if mixin_id in self._mixins:
            del self._mixins[mixin_id]
            self._on_changed()

    def add_extension_record(self, extension_record: ExtensionRecord) -> None:
        self._extensions.append(extension_record)

    def remove_extension_record(self, extension_record: ExtensionRecord) -> None:
        if extension_record in self._extensions:
            self._extensions.remove(extension_record)

    def _effective_mixins(self) -> list[Mixin]:
        parent = self.parent
        if parent is None:
            return list(self.mixins)
        direct = list(self.mixins)
        effective_from_parent = list(parent._effective_mixins())
        return list(direct) + [m for m in effective_from_parent if m not in direct]

    def _specialized_properties(self) -> list[Property]:
        super_class = self.parent
        if super_class is None:
            return list(self._direct_properties)
        helper = PropertyHelper(self._schema)
        return list(
            helper.combine_property_lists(self._direct_properties, super_class._specialized_properties())
        )

    def _update_effective_properties(self) -> None:
        if self._modified:
            self._effective_properties.clear()
            self._effective_properties.extend(self._add_mixins(self._specialized_properties()))
            self._modified = False

    def _add_mixins(self, properties: Iterable[Property]) -> Iterator[Property]:
        existing = list(properties)
        yield from properties
        for mixin_prop in self._mixin_properties():
            if not any(
                p.property_uri == mixin_prop.property_uri or p.short_code == mixin_prop.short_code for p in existing
            ):
                yield mixin_prop

    def _mixin_properties(self) -> Iterator[Property]:

        short_codes: dict[str, Mixin] = {}
        uris: dict[str, Mixin] = {}
        reverse_uris: dict[str, Mixin] = {}
        for mixin in self._effective_mixins():
            for p in mixin.properties:
                if p.short_code in short_codes:
                    raise MixinPropertyClashException("shortCode", p.short_code, short_codes[p.short_code], mixin)
                short_codes[p.short_code] = mixin

                if isinstance(p, RecordProperty) and p.reversed:
                    if p.property_uri in reverse_uris:
                        raise MixinPropertyClashException(
                            "reversed uri", p.property_uri, reverse_uris[p.property_uri], mixin
                        )
                    reverse_uris[p.property_uri] = mixin
                else:
                    if p.property_uri in uris:
                        raise MixinPropertyClashException("uri", p.property_uri, uris[p.property_uri], mixin)
                    uris[p.property_uri] = mixin
                yield p

    def all_parents(self) -> Iterator[Record]:
        """Return the inheritance chain rooted at the parent of this record.

        NOTE: the return value does not include this record, so if the record
        does not have a parent, an empty iterator is returned.
        """
        yield from self._yield_parents([self])

    def _yield_parents(self, visited: list[Record]) -> Iterator[Record]:
        ext = self.parent
        if ext is not None:
            if ext in visited:
                visited.append(ext)
                raise CircularInheritanceException(visited)
            visited.append(ext)
            yield ext
            yield from ext._yield_parents(visited)

    def has_parent(self, record_id: str, recursive: bool = True) -> bool:
        """Determine if a record with the specified ID exists as a direct or
        indirect parent of this record.

        :param record_id: the ID or short-code of the record to check for.
        :param recursive: whether to check the complete inheritance chain (True)
            or only the direct parent (False).
        """
        if recursive:
            return any(r.id == record_id for r in self.all_parents())
        return self.parent is not None and self.parent.id == record_id

    def all_descendents(self) -> list[Record]:
        """Return all records which inherit from this record, directly or indirectly."""
        descendents: list[Record] = []
        self._add_children(self, descendents)
        return descendents

    def all_descendents_and_self(self) -> list[Record]:
        """Return this record and all records which inherit from it."""
        descendents: list[Record] = [self]
        self._add_children(self, descendents)
        return descendents

    def _add_children(self, of: Record, to: list[Record]) -> None:
        for child in (r for r in self._schema.records if r.parent is not None and r.parent.id == of.id and r not in to):
            to.append(child)
            child._add_children(child, to)

    def gather_nested_records(self) -> list[Record]:
        """Return this record and all records nested (directly or indirectly) in
        the values of the properties of this record."""
        nested_records: list[Record] = [self]
        self._add_nested_records(self, nested_records)
        return nested_records

    def _add_nested_records(self, of: Record, to: list[Record]) -> None:
        for nested_property in (
            p for p in of.effective_properties if isinstance(p, RecordProperty) and p.nested
        ):
            for nested_record in (
                r for r in nested_property.range for r in r.all_descendents_and_self() if r not in to
            ):
                to.append(nested_record)
                self._add_nested_records(nested_record, to)

    def on_event(self, event: Event) -> None:
        if isinstance(event, (MixinModifiedEvent, PropertyModifiedEvent)):
            self._on_changed()

    def _on_changed(self) -> None:
        self._modified = True
        self.notify_event(RecordModifiedEvent(self))

    def validate(self) -> None:
        """Validate this record.

        :raises InvalidRecordException: if the record is not valid.
        """
        try:
            from .property import SHORT_CODE_REGEX

            if not SHORT_CODE_REGEX.fullmatch(self.short_code):
                raise InvalidShortCodeException(self.short_code)
            list(self.all_parents())
            self._update_effective_properties()
            for prop in self._effective_properties:
                prop.validate(self._schema, self)
            for ext in self._extensions:
                ext.validate(self)
        except RecordSpecException as e:
            raise InvalidRecordException(self, e) from e

    def get_property(self, short_code_or_property_uri: str) -> Property | None:
        """Get the property with the specified short-code or property IRI from
        the set of all effective properties of this record.

        :return: a :class:`Property` instance or None if there is no matching property.
        """
        return next(
            (
                p
                for p in self.effective_properties
                if p.short_code == short_code_or_property_uri or p.property_uri == short_code_or_property_uri
            ),
            None,
        )

    class Adapter(RecordAdapter):
        """The read-side adapter for a record."""

        def __init__(self, model: Record):
            self.model = model

        @property
        def id(self) -> str:
            return self.model.id

        @property
        def class_uri(self) -> str:
            return self.model.class_uri

        @property
        def short_code(self) -> str:
            return self.model.short_code

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
        def extends(self) -> str | None:
            return self.model._parent_ref

        @property
        def mixins(self) -> Iterable[str]:
            return list(self.model._mixins)

        @property
        def properties(self) -> Iterable[PropertyAdapter]:
            result: list[PropertyAdapter] = []
            for p in self.model._direct_properties:
                if isinstance(p, LiteralProperty):
                    result.append(LiteralProperty.Adapter(p))
                else:
                    assert isinstance(p, RecordProperty)
                    result.append(RecordProperty.Adapter(p))
            return result

        @property
        def extensions(self) -> Iterable[dict[str, Any]]:
            from record_spec.extensions import to_tree_with_type

            return [to_tree_with_type(ext) for ext in self.model._extensions]


def merge_record(schema: Schema, record_a: Record, record_b: Record) -> Record:
    """Create a record by merging the mixins and properties of two input records.

    :param schema: the schema to which the merged record belongs.
    :param record_a: the input record to be treated as the "base" record.
    :param record_b: the input record to be treated as the "added" record.
    :return: a new :class:`Record` which is the result of the merge.
    """
    ret = Record(schema, record_a.id, record_a.class_uri, record_a.short_code)
    all_mixins = list(record_a._mixins) + [m for m in record_b._mixins if m not in record_a._mixins]
    for mixin_id in all_mixins:
        ret.add_mixin(mixin_id)
    helper = PropertyHelper(schema)
    combined_properties = helper.combine_property_lists(record_a._direct_properties, record_b._direct_properties)
    ret._direct_properties.clear()
    ret._direct_properties.extend(combined_properties)
    return ret


__all__ = [
    "Record",
    "merge_record",
    "CircularInheritanceException",
    "IncompatiblePropertyException",
    "InvalidRecordException",
    "MixinExistsException",
    "MixinNotFoundException",
    "MixinPropertyClashException",
]