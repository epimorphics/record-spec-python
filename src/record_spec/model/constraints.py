"""Value constraints on literal and record properties."""

from __future__ import annotations

from typing import TYPE_CHECKING

from record_spec.convert import LiteralConstraintAdapter, RecordConstraintAdapter
from record_spec.exceptions import (
    InvalidLiteralConstraintException,
    InvalidRecordConstraintException,
    RecordSpecException,
)
from record_spec.values.datatypes import Datatypes

if TYPE_CHECKING:
    from collections.abc import Iterable

    from record_spec.model import Record
    from record_spec.model.resolvers import RecordResolver


class LiteralConstraint:
    """A single constraint on a literal property.

    Args:
        datatype: The IRI of the datatype that values must match.
        pattern: A regular expression pattern that values must match.
        min_inclusive: The inclusive lower bound for values.
        max_inclusive: The inclusive upper bound for values.
        min_exclusive: The exclusive lower bound for values.
        max_exclusive: The exclusive upper bound for values.
        in_: A list of allowed values.
    """

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
        self.in_: list[str] | None = in_

    def validate(self) -> None:
        """Validate the state of this constraint.

        :raises InvalidLiteralConstraintException: if a problem with the
            constraint is detected.
        """
        if self.min_inclusive is not None or self.max_inclusive is not None or (
            self.min_exclusive is not None or self.max_exclusive is not None
        ):
            datatype = Datatypes.register.get(self.datatype)
            if datatype is None:
                raise InvalidLiteralConstraintException(
                    f"Constraint with datatype {self.datatype} specifies value range constraints "
                    "but no ordering is registered for the datatype"
                )
            cmp = datatype.comparator

            def _invalid(bound_a: str, bound_b: str) -> InvalidLiteralConstraintException:
                return InvalidLiteralConstraintException(
                    f"Invalid value range constraint: {bound_a} is greater than {bound_b}."
                )
            if (
                self.min_inclusive is not None
                and self.max_inclusive is not None
                and cmp.compare(self.min_inclusive, self.max_inclusive) > 0
            ):
                raise _invalid("minInclusive", "maxInclusive")
            if (
                self.min_inclusive is not None
                and self.max_exclusive is not None
                and cmp.compare(self.min_inclusive, self.max_exclusive) > 0
            ):
                raise _invalid("minInclusive", "maxExclusive")
            if (
                self.min_exclusive is not None
                and self.max_inclusive is not None
                and cmp.compare(self.min_exclusive, self.max_inclusive) > 0
            ):
                raise _invalid("minExclusive", "maxInclusive")
            if (
                self.min_exclusive is not None
                and self.max_exclusive is not None
                and cmp.compare(self.min_exclusive, self.max_exclusive) > 0
            ):
                raise _invalid("minExclusive", "maxExclusive")

    def __repr__(self) -> str:
        return f"LiteralConstraint(datatype={self.datatype!r})"

    class Adapter(LiteralConstraintAdapter):
        """The read-side adapter for a literal constraint."""

        def __init__(self, model: LiteralConstraint):
            self.model = model

        @property
        def datatype(self) -> str:
            return self.model.datatype

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
        def values_in(self) -> Iterable[str]:
            return list(self.model.in_) if self.model.in_ is not None else []


class RecordConstraint:
    """A single constraint on a record property.

    Instances of this class are created using :meth:`RecordProperty.add_constraint`.
    """

    def __init__(self, record_resolver: RecordResolver, record_ref: str, in_: list[str] | None = None):
        self._record_resolver = record_resolver
        self.record_ref = record_ref
        self.in_: list[str] | None = in_

    @property
    def record(self) -> Record:
        """The record referenced by this constraint."""
        return self._record_resolver.resolve_record(self.record_ref)

    def validate(self) -> None:
        """Validate this constraint; ensures that the record reference resolves."""
        try:
            self._record_resolver.resolve_record(self.record_ref)
        except RecordSpecException as e:
            raise InvalidRecordConstraintException(f"Invalid record constraint: {e}", e) from e

    class Adapter(RecordConstraintAdapter):
        """The read-side adapter for a record constraint."""

        def __init__(self, model: RecordConstraint):
            self.model = model

        @property
        def record(self) -> str:
            return self.model.record.compact_id

        @property
        def values_in(self) -> list[str]:
            return list(self.model.in_) if self.model.in_ is not None else []