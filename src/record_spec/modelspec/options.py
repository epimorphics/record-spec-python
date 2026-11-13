"""Options controlling model-spec generation from a record-spec schema."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ModelSpecOptions:
    """Options controlling the model-spec output generated from a record-spec schema.

    These mirror the ``recordspec.*`` configuration properties supported by
    the model-spec repository's record-spec conversion, so that output from
    this builder remains directly comparable with output from that tool.
    """

    #: If true, mixin definitions are emitted as classes in their own right,
    #: and the mixins used by a record are emitted as its super-classes.
    include_mixins: bool = False

    #: The name to use for the synthetic rdf:type property that is added to
    #: every generated class.
    type_property: str = "@type"
