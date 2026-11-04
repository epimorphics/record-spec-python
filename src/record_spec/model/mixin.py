"""Mixin definitions: reusable collections of properties transcluded onto records."""

from __future__ import annotations

from typing import TYPE_CHECKING

from record_spec.convert import MixinAdapter, PropertyAdapter
from record_spec.exceptions import InvalidMixinException, PropertyClashException, RecordSpecException
from record_spec.model.events import Event, EventListener, EventSourceMixin, MixinModifiedEvent, PropertyModifiedEvent

from .base import Documentable, Extensible, PropertyFactory
from .property import LiteralProperty, Property, RecordProperty
from .property_helper import PropertyHelper
from .values import LangString

if TYPE_CHECKING:
    from collections.abc import Iterable
    from typing import Any

    from record_spec.extensions import ExtensionRecord

    from .property_mapping import PropertyMapping
    from .resolvers import RecordResolver
    from .schema import Schema


class Mixin(Documentable, Extensible, EventListener, EventSourceMixin, PropertyFactory):
    """Represents a mixin that provides properties which can be reused by records."""

    def __init__(self, record_resolver: RecordResolver, mixin_id: str):
        super().__init__()
        self._init_listeners()
        self._record_resolver = record_resolver
        self.id = mixin_id
        self._properties: list[Property] = []
        self._extensions: list[ExtensionRecord] = []

    @property
    def properties(self) -> Iterable[Property]:
        """The properties which are defined on this mixin."""
        return list(self._properties)

    @property
    def extensions(self) -> Iterable[ExtensionRecord]:
        """The extension records that annotate this mixin."""
        return list(self._extensions)

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
        p = RecordProperty(
            self._record_resolver, short_code, uri, required, repeatable, nested, reversed, property_mapping
        )
        self._add_property(p)
        return p

    def create_literal_property(
        self,
        short_code: str,
        uri: str,
        required: bool = False,
        repeatable: bool = False,
    ) -> LiteralProperty:
        p = LiteralProperty(short_code, uri, required, repeatable)
        self._add_property(p)
        return p

    def _add_property(self, prop: Property) -> None:
        clash = next(
            (p for p in self._properties if p.short_code == prop.short_code or p.property_uri == prop.property_uri),
            None,
        )
        if clash is not None:
            raise PropertyClashException(clash, prop)
        self._properties.append(prop)
        prop.add_listener(self)
        self._on_changed()

    def remove_property(self, prop: Property | str) -> None:
        """Remove the specified property (by short-code or instance) from this mixin.

        If the argument does not identify a property of this mixin, this method
        completes without modifying the mixin.
        """
        if isinstance(prop, str):
            prop_short_code = prop
            match = next((p for p in self._properties if p.short_code == prop_short_code), None)
            if match is not None:
                self._properties.remove(match)
                self._on_changed()
            return
        if prop in self._properties:
            self._properties.remove(prop)
            self._on_changed()

    def add_extension_record(self, extension_record: ExtensionRecord) -> None:
        self._extensions.append(extension_record)
        self._on_changed()

    def remove_extension_record(self, extension_record: ExtensionRecord) -> None:
        if extension_record in self._extensions:
            self._extensions.remove(extension_record)
            self._on_changed()

    def _on_changed(self) -> None:
        self.notify_event(MixinModifiedEvent(self))

    def on_event(self, event: Event) -> None:
        if isinstance(event, PropertyModifiedEvent):
            self._on_changed()

    def clone(self, schema: Schema) -> Mixin:
        """Create a copy of this mixin belonging to ``schema``."""
        from .property import clone_property

        ret = schema.create_mixin(self.id)
        for prop in self.properties:
            clone_property(ret, prop)
        return ret

    def validate(self) -> None:
        """Validate this mixin and its contents.

        :raises InvalidMixinException: if the mixin is not valid.
        """
        try:
            for extension in self._extensions:
                extension.validate(self)
        except RecordSpecException as e:
            raise InvalidMixinException(self, e) from e

    class Adapter(MixinAdapter):
        """The read-side adapter for a mixin."""

        def __init__(self, model: Mixin):
            self.model = model

        @property
        def id(self) -> str:
            return self.model.id

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
        def properties(self) -> Iterable[PropertyAdapter]:
            result: list[PropertyAdapter] = []
            for p in self.model.properties:
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


def merge_mixin(resolver: RecordResolver, mixin_id: str, mixin_a: Mixin, mixin_b: Mixin) -> Mixin:
    """Create a new :class:`Mixin` which is the result of merging two mixins."""
    ret = Mixin(resolver, mixin_id)
    helper = PropertyHelper(resolver)
    ret._properties.extend(helper.combine_property_lists(mixin_a._properties, mixin_b._properties))
    return ret