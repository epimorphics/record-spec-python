"""Property definitions: `Property`, `LiteralProperty`, `RecordProperty` and `PropertyKind`."""

from __future__ import annotations

import re
from enum import Enum
from typing import TYPE_CHECKING

from record_spec.convert import PropertyAdapter
from record_spec.exceptions import (
    InvalidPropertyException,
    InvalidPropertyMapException,
    InvalidReversePropertyRangeException,
    InvalidShortCodeException,
    RecordSpecException,
)
from record_spec.model.events import EventSourceMixin, PropertyModifiedEvent

from .base import Documentable, Extensible
from .constraints import LiteralConstraint, RecordConstraint

if TYPE_CHECKING:
    from collections.abc import Iterable
    from typing import Any

    from record_spec.convert import (
        LiteralConstraintAdapter,
        PropertyMappingAdapter,
        RecordConstraintAdapter,
    )
    from record_spec.extensions import ExtensionRecord
    from record_spec.model import Record
    from record_spec.model.resolvers import RecordResolver
    from record_spec.model.values import LangString

    from .base import PropertyFactory
    from .property_mapping import PropertyMapping

#: The pattern that all short-codes must match.
SHORT_CODE_REGEX = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*")


class PropertyKind(Enum):
    """Enumerates the different kinds of properties supported by the model."""

    OBJECT = "object"
    LITERAL = "literal"


class Property(Documentable, Extensible, EventSourceMixin):
    """Base class for representing property definitions.

    Args:
        short_code: The short-code identifier for the property.
        property_uri: The IRI of the predicate for this property.
        kind: The kind of property (literal or object).
        required: True if the property must appear on the parent record instance.
        repeatable: True if the property may appear more than once on the parent
            record instance.
    """

    def __init__(
        self,
        short_code: str,
        property_uri: str,
        kind: PropertyKind,
        required: bool = False,
        repeatable: bool = False,
    ):
        super().__init__()
        self._init_listeners()
        self.short_code = short_code
        self.property_uri = property_uri
        self.kind = kind
        self.required = required
        self.repeatable = repeatable
        self._extensions: list[ExtensionRecord] = []

    @property
    def extensions(self) -> Iterable[ExtensionRecord]:
        return list(self._extensions)

    def add_extension_record(self, extension_record: ExtensionRecord) -> None:
        self._extensions.append(extension_record)

    def remove_extension_record(self, extension_record: ExtensionRecord) -> None:
        if extension_record in self._extensions:
            self._extensions.remove(extension_record)

    def validate(self, resolver: RecordResolver, parent: Record) -> None:
        try:
            self._validate_short_code()
            self._validate_internal(resolver, parent)
            for extension in self._extensions:
                extension.validate(self)
        except RecordSpecException as e:
            raise InvalidPropertyException(self, e) from e

    def _validate_short_code(self) -> None:
        if not SHORT_CODE_REGEX.fullmatch(self.short_code):
            raise InvalidShortCodeException(self.short_code)

    def _validate_internal(self, resolver: RecordResolver, parent: Record) -> None:
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"{self.__class__.__module__}.{self.__class__.__qualname__}:{self.short_code}"


class LiteralProperty(Property):
    """Represents a single literal property."""

    def __init__(
        self,
        short_code: str,
        uri: str,
        required: bool = False,
        repeatable: bool = False,
        constraints: Iterable[LiteralConstraint] | None = None,
    ):
        super().__init__(short_code, uri, PropertyKind.LITERAL, required, repeatable)
        self._constraints: list[LiteralConstraint] = list(constraints) if constraints is not None else []

    @property
    def constraints(self) -> list[LiteralConstraint]:
        """The list of constraints defined on this property."""
        return list(self._constraints)

    @property
    def range(self) -> list[str]:
        """The distinct set of datatypes covered by all the constraints on this property."""
        return list(dict.fromkeys(c.datatype for c in self._constraints))

    def add_constraint(
        self,
        datatype: str,
        pattern: str | None = None,
        min_inclusive: str | None = None,
        max_inclusive: str | None = None,
        min_exclusive: str | None = None,
        max_exclusive: str | None = None,
        in_: list[str] | None = None,
    ) -> LiteralConstraint:
        """Add a constraint to this property and return it."""
        constraint = LiteralConstraint(
            datatype, pattern, min_inclusive, max_inclusive, min_exclusive, max_exclusive, in_
        )
        self._constraints.append(constraint)
        self._on_changed()
        return constraint

    def remove_constraint(self, constraint: LiteralConstraint | int) -> None:
        """Remove the specified constraint (or the constraint at the given index).

        If the argument does not identify a constraint in :attr:`constraints`,
        this method returns without modifying the property.
        """
        if isinstance(constraint, int):
            constraint_ix = constraint
            if 0 <= constraint_ix < len(self._constraints):
                self._constraints.pop(constraint_ix)
                self._on_changed()
            return
        if constraint in self._constraints:
            self._constraints.remove(constraint)
            self._on_changed()

    def _on_changed(self) -> None:
        self.notify_event(PropertyModifiedEvent(self))

    def accepts(self, datatype: str) -> bool:
        """Return True if this property is open-ranged, or its range includes ``datatype``."""
        return not self._constraints or any(c.datatype == datatype for c in self._constraints)

    def _validate_internal(self, resolver: RecordResolver, parent: Record) -> None:
        for constraint in self._constraints:
            constraint.validate()

    class Adapter(PropertyAdapter):
        def __init__(self, model: LiteralProperty):
            self.model = model

        @property
        def property_uri(self) -> str:
            return self.model.property_uri

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
        def required(self) -> bool:
            return self.model.required

        @property
        def repeatable(self) -> bool:
            return self.model.repeatable

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
            return [LiteralConstraint.Adapter(c) for c in self.model.constraints]

        @property
        def record_constraints(self) -> Iterable[RecordConstraintAdapter]:
            return []

        @property
        def property_map(self) -> PropertyMappingAdapter | None:
            return None

        @property
        def extensions(self) -> Iterable[dict[str, Any]]:
            from record_spec.extensions import to_tree_with_type

            return [to_tree_with_type(ext) for ext in self.model.extensions]


class RecordProperty(Property):
    """Represents a property definition for a property with a range over records.

    Instances of this class are created using :meth:`Record.create_record_property`.
    """

    def __init__(
        self,
        record_resolver: RecordResolver,
        short_code: str,
        uri: str,
        required: bool = False,
        repeatable: bool = False,
        nested: bool = False,
        reversed: bool = False,
        property_mapping: PropertyMapping | None = None,
        constraints: Iterable[RecordConstraint] | None = None,
    ):
        super().__init__(short_code, uri, PropertyKind.OBJECT, required, repeatable)
        self._record_resolver = record_resolver
        self.nested = nested
        self.reversed = reversed
        self._property_map = property_mapping
        self._constraints: list[RecordConstraint] = list(constraints) if constraints is not None else []

    @property
    def constraints(self) -> list[RecordConstraint]:
        """The constraints defined on this property."""
        return list(self._constraints)

    @property
    def range(self) -> list[Record]:
        """The distinct set of records in the constraints of this property."""
        return list(dict.fromkeys(c.record for c in self._constraints))

    @property
    def property_mapping(self) -> PropertyMapping | None:
        return self._property_map

    def add_constraint(self, record_id: str, allowed_values: list[str] | None = None) -> RecordConstraint:
        """Create and add a new :class:`RecordConstraint` for this property."""
        constraint = RecordConstraint(self._record_resolver, record_id, allowed_values)
        self._constraints.append(constraint)
        self._on_changed()
        return constraint

    def remove_constraint(self, constraint: RecordConstraint | int) -> None:
        """Remove the specified constraint (or the constraint at the given index).

        If the argument does not identify a constraint in :attr:`constraints`,
        this method returns without modifying the property.
        """
        if isinstance(constraint, int):
            constraint_ix = constraint
            if 0 <= constraint_ix < len(self._constraints):
                self._constraints.pop(constraint_ix)
                self._on_changed()
            return
        if constraint in self._constraints:
            self._constraints.remove(constraint)
            self._on_changed()

    def set_property_map(self, property_mapping: PropertyMapping | None) -> None:
        self._property_map = property_mapping
        self._on_changed()

    def _on_changed(self) -> None:
        self.notify_event(PropertyModifiedEvent(self))

    def _validate_internal(self, resolver: RecordResolver, parent: Record) -> None:
        if self.reversed:
            self._validate_reverse_property_range(parent)
        if self._property_map is not None:
            self._validate_property_map(self._property_map)
        for constraint in self._constraints:
            constraint.validate()

    def _validate_reverse_property_range(self, parent: Record) -> None:
        from .property import LiteralProperty as _LP

        for record_in_range in (c.record for c in self._constraints):
            forward_property = record_in_range.get_property(self.property_uri)
            if isinstance(forward_property, _LP):
                raise InvalidReversePropertyRangeException(
                    f"Reversed property {self.short_code} includes record {record_in_range.short_code} in its "
                    f"range, but that record uses the same property URI ({self.property_uri}) for a literal "
                    "property which cannot be reversed."
                )
            if isinstance(forward_property, RecordProperty):
                fwd_range = list(forward_property.range)
                if (
                    fwd_range
                    and parent not in fwd_range
                    and not any(parent_ in fwd_range for parent_ in parent.all_parents())
                ):
                    raise InvalidReversePropertyRangeException(
                        f"Reversed property {self.short_code} includes record {record_in_range.short_code} in its "
                        f"range, but that record uses the same Property URI ({self.property_uri}) for a property "
                        f"which does not include {record_in_range.short_code} in its range."
                    )

    def _validate_property_map(self, property_mapping: PropertyMapping) -> None:
        if not self.nested:
            raise InvalidPropertyMapException(
                self, property_mapping, "A property map cannot be specified on a reference property."
            )
        if property_mapping.key_property == "@id":
            # @id is always a valid key property
            return
        key_properties = [r.get_property(property_mapping.key_property) for r in self.range]
        if any(p is None for p in key_properties):
            raise InvalidPropertyMapException(
                self,
                property_mapping,
                "At least one record in the property range does not support the key property "
                f"`{property_mapping.key_property}`.",
            )
        if any(p.kind == PropertyKind.OBJECT for p in key_properties):  # type: ignore[union-attr]
            raise InvalidPropertyMapException(
                self,
                property_mapping,
                "At least one record in the property range has a non-literal key property "
                f"`{property_mapping.key_property}`.",
            )
        if any(p.repeatable for p in key_properties):  # type: ignore[union-attr]
            raise InvalidPropertyMapException(
                self,
                property_mapping,
                "At least one record in the property range allows the key property "
                f"`{property_mapping.key_property}` to be repeatable.",
            )
        if any(not p.required for p in key_properties):  # type: ignore[union-attr]
            raise InvalidPropertyMapException(
                self,
                property_mapping,
                "At least one record in the property range allows the key property "
                f"`{property_mapping.key_property}` to be optional.",
            )

    class Adapter(PropertyAdapter):
        def __init__(self, model: RecordProperty):
            self.model = model

        @property
        def property_uri(self) -> str:
            return self.model.property_uri

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
        def required(self) -> bool:
            return self.model.required

        @property
        def repeatable(self) -> bool:
            return self.model.repeatable

        @property
        def kind(self) -> PropertyKind:
            return PropertyKind.OBJECT

        @property
        def nested(self) -> bool | None:
            return self.model.nested

        @property
        def reversed(self) -> bool | None:
            return self.model.reversed

        @property
        def literal_constraints(self) -> Iterable[LiteralConstraintAdapter]:
            return []

        @property
        def record_constraints(self) -> Iterable[RecordConstraintAdapter]:
            return [RecordConstraint.Adapter(c) for c in self.model.constraints]

        @property
        def property_map(self) -> PropertyMappingAdapter | None:
            from .property_mapping import PropertyMapping

            return PropertyMapping.Adapter(self.model.property_mapping) if self.model.property_mapping else None

        @property
        def extensions(self) -> Iterable[dict[str, Any]]:
            from record_spec.extensions import to_tree_with_type

            return [to_tree_with_type(ext) for ext in self.model.extensions]


def clone_property(property_factory: PropertyFactory, prop: Property) -> None:
    """Create a copy of ``prop`` on the given :class:`PropertyFactory`."""
    if isinstance(prop, LiteralProperty):
        clone = property_factory.create_literal_property(
            prop.short_code, prop.property_uri, prop.required, prop.repeatable
        )
        for constraint in prop.constraints:
            clone.add_constraint(
                constraint.datatype,
                constraint.pattern,
                constraint.min_inclusive,
                constraint.max_inclusive,
                constraint.min_exclusive,
                constraint.max_exclusive,
                constraint.in_,
            )
        _copy_documentation(prop, clone)
    else:
        assert isinstance(prop, RecordProperty)
        clone_rec = property_factory.create_record_property(
            prop.short_code,
            prop.property_uri,
            prop.required,
            prop.repeatable,
            prop.nested,
            prop.reversed,
            prop.property_mapping,
        )
        for rec_constraint in prop.constraints:
            clone_rec.add_constraint(rec_constraint.record_ref, rec_constraint.in_)
        _copy_documentation(prop, clone_rec)


def _copy_documentation(source: Property, target: Property) -> None:
    """Copy label/summary/description from one property to another (#58 upstream)."""
    from .values import LangString

    target.label.extend(LangString(ls.value, ls.language) for ls in source.label)
    target.summary.extend(LangString(ls.value, ls.language) for ls in source.summary)
    target.description.extend(LangString(ls.value, ls.language) for ls in source.description)