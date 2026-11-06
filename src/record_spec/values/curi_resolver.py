"""CURI (compact URI) resolution: expanding ``prefix:rest`` and compacting full IRIs."""

from __future__ import annotations

from abc import ABC, abstractmethod
from urllib.parse import urljoin, urlsplit

from record_spec.exceptions import UriResolutionException


class CuriResolver(ABC):
    """The interface implemented by objects that can resolve and compact CURIs."""

    @property
    @abstractmethod
    def base_uri(self) -> str | None:
        """The base URI used when resolving relative IRI references."""

    @abstractmethod
    def set_base(self, base_uri: str) -> None:
        """Set the base URI to use when resolving relative IRI references."""

    @abstractmethod
    def resolve(self, curi: str) -> str:
        """Expand a CURI or relative reference into a full IRI."""

    @abstractmethod
    def compact(self, uri: str) -> str:
        """Compact a full IRI into a CURI or relative reference where possible."""


class CuriResolverImpl(CuriResolver):
    """A :class:`CuriResolver` backed by a fixed set of prefix mappings."""

    def __init__(self, prefix_mappings: dict[str, str], base_uri: str | None = None):
        self._prefix_mappings = dict(prefix_mappings)
        self._base_uri = base_uri
        # Kotlin's associateBy keeps the *last* prefix for a duplicated URI;
        # mirror that by iterating in insertion order and letting later
        # entries overwrite earlier ones.
        self._reverse: dict[str, str] = {}
        for prefix, uri in self._prefix_mappings.items():
            self._reverse[uri] = prefix

    @property
    def base_uri(self) -> str | None:
        return self._base_uri

    def set_base(self, base_uri: str) -> None:
        self._base_uri = base_uri

    def resolve(self, curi: str) -> str:
        if ":" in curi:
            prefix, rest = curi.split(":", 1)
            if prefix in self._prefix_mappings:
                return self._prefix_mappings[prefix] + rest
        if urlsplit(curi).scheme:
            return curi
        if self._base_uri is not None:
            return urljoin(self._base_uri, curi)
        raise UriResolutionException(f"URI {curi} is a relative URI and there is no in-scope base URI to resolve against.")

    def compact(self, uri: str) -> str:
        split_at = max(uri.rfind("#"), uri.rfind("/"))
        if split_at != -1:
            prefix, suffix = uri[: split_at + 1], uri[split_at + 1 :]
            if prefix in self._reverse:
                return f"{self._reverse[prefix]}:{suffix}"
        if self._base_uri is not None:
            base_dir = urljoin(self._base_uri, ".")
            if uri.startswith(base_dir):
                return uri[len(base_dir) :]
        return uri