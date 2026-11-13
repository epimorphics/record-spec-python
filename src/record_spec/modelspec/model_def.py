"""Model-spec definitions generated from a record-spec schema.

The Python equivalent of the Kotlin upstream ``modelspec/ModelDef.kt``: the
field names and serialization shapes match the model-spec YAML representation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PropertyType(Enum):
    """The kind of a property in a model-spec definition.

    The enum values are the lower-case forms used in model-spec YAML documents
    (the upstream Kotlin constants serialize via ``@JsonProperty("object")``
    and ``@JsonProperty("datatype")``).
    """

    #: A property whose values are resources or blank nodes.
    OBJECT = "object"

    #: A property whose values are literals.
    DATATYPE = "datatype"


@dataclass
class PropertyDef:
    """A model-spec definition of a property.

    The serialized field names match the model-spec YAML representation:
    ``prop`` for the property URI, ``type`` for the range (single value or
    list), and null values omitted.
    """

    uri: str
    name: str | None = None
    kind: PropertyType | None = None
    types: list[str] | None = None
    optional: bool | None = None
    multi: bool | None = None
    unique: bool | None = None
    value_base: str | None = None
    comment: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return the model-spec YAML representation of this property definition.

        Mirrors the upstream Jackson serialization: ``uri`` is serialized as
        ``prop``, empty/null ``types`` are omitted, and a single-element
        ``types`` list is written unwrapped as a scalar.
        """
        d: dict[str, Any] = {"prop": self.uri}
        if self.name is not None:
            d["name"] = self.name
        if self.kind is not None:
            d["kind"] = self.kind.value
        if self.types:
            d["type"] = self.types[0] if len(self.types) == 1 else list(self.types)
        if self.optional is not None:
            d["optional"] = self.optional
        if self.multi is not None:
            d["multi"] = self.multi
        if self.unique is not None:
            d["unique"] = self.unique
        if self.value_base is not None:
            d["valueBase"] = self.value_base
        if self.comment is not None:
            d["comment"] = self.comment
        return d


@dataclass
class ClassDef:
    """A model-spec definition of a class.

    The serialized field names match the model-spec YAML representation:
    ``class`` for the class URI, ``properties`` for the property list, and
    single-element ``sub_class_of`` lists written unwrapped.
    """

    uri: str
    name: str | None = None
    sub_class_of: list[str] | None = None
    properties: list[PropertyDef] = field(default_factory=list)
    scheme: str | None = None
    value_base: str | None = None
    comment: str | None = None
    polymorphic: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return the model-spec YAML representation of this class definition.

        Mirrors the upstream Jackson serialization: ``uri`` is serialized as
        ``class``, ``properties`` is always present, and a single-element
        ``sub_class_of`` list is written unwrapped as a scalar.
        """
        d: dict[str, Any] = {"class": self.uri}
        if self.name is not None:
            d["name"] = self.name
        if self.sub_class_of is not None:
            d["subClassOf"] = self.sub_class_of[0] if len(self.sub_class_of) == 1 else list(self.sub_class_of)
        d["properties"] = [prop.to_dict() for prop in self.properties]
        if self.scheme is not None:
            d["scheme"] = self.scheme
        if self.value_base is not None:
            d["valueBase"] = self.value_base
        if self.comment is not None:
            d["comment"] = self.comment
        if self.polymorphic is not None:
            d["polymorphic"] = self.polymorphic
        return d


@dataclass
class ModelDef:
    """A model-spec document generated from a record-spec schema.

    The serialized field names match the model-spec YAML representation: a
    prefix map, a list of class definitions and an optional top-level comment.
    """

    prefixes: dict[str, str] | None = None
    classes: list[ClassDef] = field(default_factory=list)
    comment: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return the model-spec YAML representation of this model definition.

        Mirrors the upstream Jackson serialization: ``classes`` is always
        present, null ``prefixes`` and ``comment`` are omitted.
        """
        d: dict[str, Any] = {}
        if self.prefixes is not None:
            d["prefixes"] = dict(self.prefixes)
        d["classes"] = [cls.to_dict() for cls in self.classes]
        if self.comment is not None:
            d["comment"] = self.comment
        return d
