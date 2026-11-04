"""Options for rdf-mapper template generation (the Kotlin ``RdfMapperOptions``)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RdfMapperOptions:
    """Options controlling rdf-mapper template output."""

    #: Whether the rdf-mapper output should use ``@graphAdd`` instead of
    #: ``@graph`` for graph-targeted updates.
    graph_add: bool = False

    #: The pattern to generate the target graph for an update. This may use
    #: properties from the root record of the mapping. If not specified, the
    #: rdf-mapper output will not include an ``@graph`` or ``@graphAdd``
    #: property for the mapping of the root record. If specified, the output
    #: will include an ``@graphAdd`` if :attr:`graph_add` is True, or an
    #: ``@graph`` otherwise.
    graph_pattern: str | None = None