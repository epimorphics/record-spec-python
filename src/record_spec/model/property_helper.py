"""Utilities for processing inheritance and mixin composition of properties.

This is a faithful translation of the algorithms specified in
``docs/record-spec-model.md`` of the Kotlin original:
``CombinePropertyLists``, ``CombineProperties``, ``CombineLiteralProperties``,
``CombineLiteralConstraints``, ``MergeLiteralConstraints``,
``CombineRecordProperties``, ``CombineRecordConstraints``, ``MergeRecordConstraints``
and ``MergePropertyMappings``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeVar

from record_spec.exceptions import (
    IncompatiblePropertyException,
    IncompatiblePropertyMapsException,
    IncompatibleRangeException,
    NoComparatorException,
    PropertyClashException,
)
from record_spec.values import Comparator
from record_spec.values.datatypes import Datatypes

from .constraints import LiteralConstraint, RecordConstraint
from .property import LiteralProperty, Property, PropertyKind, RecordProperty

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Iterator

    from record_spec.model.resolvers import RecordResolver

    from .property_mapping import PropertyMapping


V = TypeVar("V")


def _combine_values(val_a: V | None, val_b: V | None, combine: Callable[[V, V], V | None]) -> V | None:
    """Apply the CombineValue rules: use whichever value is non-null, combining when both are present."""
    if val_a is not None:
        return combine(val_a, val_b) if val_b is not None else val_a
    return val_b


class PropertyHelper:
    """Provides utility methods to assist in processing inheritance and mixins."""

    def __init__(self, record_resolver: RecordResolver):
        self._record_resolver = record_resolver

    def combine_property_lists(self, list_a: Iterable[Property], list_b: Iterable[Property]) -> Iterator[Property]:
        """Return the result of combining two lists of properties (lazily).

        Raises on clashes where a property matches in short-code *or* URI but not both.
        """
        list_a = list(list_a)
        list_b = list(list_b)
        for pa in list_a:
            valid_overload = next(
                (pb for pb in list_b if pb.property_uri == pa.property_uri and pb.short_code == pa.short_code), None
            )
            if valid_overload is not None:
                yield self._combine_properties(pa, valid_overload)
            else:
                invalid_overload = next(
                    (
                        pb
                        for pb in list_b
                        if (pb.property_uri == pa.property_uri and pb.short_code != pa.short_code)
                        or (pb.short_code == pa.short_code and pb.property_uri != pa.property_uri)
                    ),
                    None,
                )
                if invalid_overload is not None:
                    raise PropertyClashException(pa, invalid_overload)
                yield pa
        for pb in list_b:
            if not any(pa.short_code == pb.short_code or pa.property_uri == pb.property_uri for pa in list_a):
                yield pb

    def _combine_properties(self, pa: Property, pb: Property) -> Property:
        if pa.kind == PropertyKind.LITERAL and pb.kind == PropertyKind.LITERAL:
            return self._combine_literal_properties(pa, pb)  # type: ignore[arg-type]
        if pa.kind == PropertyKind.OBJECT and pb.kind == PropertyKind.OBJECT:
            return self._combine_record_properties(pa, pb)  # type: ignore[arg-type]
        raise IncompatiblePropertyException(pa, pb, "Cannot combine a Literal property and a Record property.")

    def _combine_literal_properties(self, pa: LiteralProperty, pb: LiteralProperty) -> LiteralProperty:
        try:
            return LiteralProperty(
                pa.short_code,
                pa.property_uri,
                pa.required or pb.required,
                pa.repeatable and pb.repeatable,
                self._combine_literal_constraints(pa.constraints, pb.constraints),
            )
        except IncompatibleRangeException as e:
            raise IncompatiblePropertyException(pa, pb, str(e) or "Incompatible value ranges", e) from e

    def _combine_record_properties(self, pa: RecordProperty, pb: RecordProperty) -> RecordProperty:
        if pa.nested != pb.nested:
            raise IncompatiblePropertyException(
                pa, pb, "Cannot combine a nested record property with a reference record property."
            )
        if pa.reversed != pb.reversed:
            raise IncompatiblePropertyException(
                pa, pb, "Cannot combine a reversed record property with a non-reversed record property."
            )
        return RecordProperty(
            self._record_resolver,
            pa.short_code,
            pa.property_uri,
            pa.required or pb.required,
            pa.repeatable and pb.repeatable,
            pa.nested,
            pa.reversed,
            _combine_values(pa.property_mapping, pb.property_mapping, self._merge_property_mappings),
            self._combine_record_constraints(pa.constraints, pb.constraints),
        )

    def _merge_property_mappings(self, map_a: PropertyMapping, map_b: PropertyMapping) -> PropertyMapping:
        from .property_mapping import PropertyMapping

        if map_a.key_property != map_b.key_property:
            raise IncompatiblePropertyMapsException(map_a, map_b)
        return PropertyMapping(map_a.key_property)

    def _combine_literal_constraints(
        self, list_a: list[LiteralConstraint], list_b: list[LiteralConstraint]
    ) -> list[LiteralConstraint]:
        result: list[LiteralConstraint] = []
        if not list_a:
            return list(list_b)
        if not list_b:
            return list(list_a)
        for ca in list_a:
            for cb in (cb for cb in list_b if cb.datatype == ca.datatype):
                merged = self._merge_literal_constraints(ca, cb)
                if merged is not None:
                    result.append(merged)
        if not result:
            raise IncompatibleRangeException("There is no overlap between the property constraints")
        return result

    def _merge_literal_constraints(self, ca: LiteralConstraint, cb: LiteralConstraint) -> LiteralConstraint | None:
        cc = LiteralConstraint(
            ca.datatype,
            _combine_values(ca.pattern, cb.pattern, lambda a, b: f"(?={a})(?={b})"),
            self._max(ca.datatype, ca.min_inclusive, cb.min_inclusive),
            self._min(ca.datatype, ca.max_inclusive, cb.max_inclusive),
            self._max(ca.datatype, ca.min_exclusive, cb.min_exclusive),
            self._min(ca.datatype, ca.max_exclusive, cb.max_exclusive),
            _combine_values(
                ca.in_,
                cb.in_,
                lambda a, b: [v for v in a if v in set(b)],
            ),
        )
        if ca.in_ is not None and cb.in_ is not None and not cc.in_:
            return None
        # Check value range is valid
        if cc.min_inclusive is not None:
            if cc.max_inclusive is not None and self._compare(ca.datatype, cc.min_inclusive, cc.max_inclusive) > 0:
                return None
            if cc.max_exclusive is not None and self._compare(ca.datatype, cc.min_inclusive, cc.max_exclusive) > 0:
                return None
        if cc.min_exclusive is not None:
            if cc.max_inclusive is not None and self._compare(ca.datatype, cc.min_exclusive, cc.max_inclusive) > 0:
                return None
            if cc.max_exclusive is not None and self._compare(ca.datatype, cc.min_exclusive, cc.max_exclusive) > 0:
                return None
        return cc

    def _combine_record_constraints(
        self, list_a: list[RecordConstraint], list_b: list[RecordConstraint]
    ) -> list[RecordConstraint]:
        result: list[RecordConstraint] = []
        for ca in list_a:
            record_a = ca.record
            for cb in list_b:
                record_b = cb.record
                if record_a == record_b or record_a.has_parent(record_b.id):
                    merged = self._merge_record_constraints(ca, cb)
                    if merged is not None:
                        result.append(merged)
                elif record_b.has_parent(record_a.id):
                    merged = self._merge_record_constraints(cb, ca)
                    if merged is not None:
                        result.append(merged)
        return result

    def _merge_record_constraints(
        self, derived: RecordConstraint, parent: RecordConstraint
    ) -> RecordConstraint | None:
        merged_in = _combine_values(
            derived.in_,
            parent.in_,
            lambda a, b: [v for v in a if v in set(b)],
        )
        if merged_in is not None and not merged_in and derived.in_ is not None and parent.in_ is not None:
            return None
        return RecordConstraint(self._record_resolver, derived.record.id, merged_in)

    def _max(self, datatype: str, val_a: str | None, val_b: str | None) -> str | None:
        return _combine_values(val_a, val_b, lambda a, b: self._comparator(datatype).max(a, b))

    def _min(self, datatype: str, val_a: str | None, val_b: str | None) -> str | None:
        return _combine_values(val_a, val_b, lambda a, b: self._comparator(datatype).min(a, b))

    def _compare(self, datatype: str, val_a: str, val_b: str) -> int:
        return self._comparator(datatype).compare(val_a, val_b)

    def _comparator(self, datatype: str) -> Comparator[Any]:
        datatype_entry = Datatypes.register.get(datatype)
        if datatype_entry is None:
            raise NoComparatorException(datatype)
        return datatype_entry.comparator