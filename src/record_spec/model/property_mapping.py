"""A property mapping: configuration for a dictionary-valued record property."""

from __future__ import annotations

from dataclasses import dataclass

from record_spec.convert import PropertyMappingAdapter


@dataclass
class PropertyMapping:
    """Specifies that a nested record property should be treated as a map/dictionary.

    ``key_property`` must be the short-code of a required, non-repeatable
    literal property on all the records in the range of the mapped property,
    or the special value ``"@id"`` to key by the IRI of the value resource.
    """

    key_property: str

    def __str__(self) -> str:
        return f"{{ keyProperty: {self.key_property} }}"

    class Adapter(PropertyMappingAdapter):
        """The read-side adapter for a property mapping."""

        def __init__(self, model: PropertyMapping):
            self.model = model

        @property
        def key_property(self) -> str:
            return self.model.key_property

        def __repr__(self) -> str:
            return f"PropertyMapping.Adapter({self.model!r})"