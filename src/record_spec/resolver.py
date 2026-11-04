"""Schema resolution for `imports:` processing.

The concrete resolvers (:class:`BasicSchemaResolver`, :class:`CachingSchemaResolver`)
are implemented in milestone M2; this module defines the interface they implement.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from record_spec.model import Schema


class SchemaResolver(ABC):
    """The interface implemented by objects that can retrieve a schema by URI."""

    @abstractmethod
    def resolve(self, schema_uri: str) -> Schema:
        """Retrieve the schema identified by ``schema_uri``.

        The returned schema is expected to have its imports resolved as needed
        by the caller (:meth:`Schema.resolve_imports`).
        """