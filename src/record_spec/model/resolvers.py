"""Interfaces for resolving records and mixins by identifier."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from record_spec.exceptions import MixinNotFoundException, RecordNotFoundException

if TYPE_CHECKING:
    from record_spec.model import Mixin, Record


class RecordResolver(ABC):
    """The interface implemented by objects that support the lookup of records."""

    @abstractmethod
    def resolve_record(self, record_id: str) -> Record:
        """Get the record whose ID is ``record_id``.

        :raises RecordNotFoundException: if no record matching ``record_id`` is found.
        """

    @abstractmethod
    def resolve_record_by_class_uri(self, class_uri: str) -> Record:
        """Get the record whose associated RDF class URI is ``class_uri``.

        :raises RecordNotFoundException: if no record with a class URI matching
            ``class_uri`` is found.
        """


class MixinResolver(ABC):
    """The interface implemented by objects that can locate mixins by ID."""

    @abstractmethod
    def resolve_mixin(self, mixin_id: str) -> Mixin:
        """Return the mixin with the specified ID.

        :raises MixinNotFoundException: when no mixin with an ID matching
            ``mixin_id`` can be found.
        """


__all__ = ["RecordResolver", "MixinResolver", "RecordNotFoundException", "MixinNotFoundException"]