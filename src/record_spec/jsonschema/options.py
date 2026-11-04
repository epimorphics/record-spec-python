"""JSON Schema generation options (the Kotlin ``JsonOptions``)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class JsonOptions:
    """Options controlling JSON Schema and JSON-LD context generation.

    Mirrors the Kotlin ``JsonOptions``.
    """

    #: Whether resource references are written as a bare URI string, e.g.
    #: ``"http://example.org/foo"`` (True), or as an object with an id
    #: property, e.g. ``{"@id": "http://example.org/foo"}`` (False).
    bare_reference_ids: bool = False

    #: The property used to specify the IRI of a resource.
    id_property: str = "@id"

    #: The property used to specify the type of a resource, or the data-type
    #: of a data-typed literal.
    type_property: str = "@type"

    #: The property used to specify the value of a data-typed or
    #: language-tagged literal.
    value_property: str = "@value"

    #: The property used to specify the language tag of a language-tagged
    #: literal.
    language_property: str = "@language"

    #: Whether the type property (@type) may be optional when only a single
    #: value is possible. With the default False, all objects and nested
    #: objects require the type property in the generated JSON schema.
    optional_type_property: bool = False

    #: Whether to include all subclasses of a record definition in the
    #: JSON schema generated for the record definition.
    with_subclasses: bool = True

    #: Whether to allow validation of an array of records as the top-level
    #: value in the JSON schema.
    allow_array: bool = False

    #: Whether to require that the top-level value in the JSON schema is an
    #: array of values. Overrides :attr:`allow_array`.
    require_array: bool = False

    #: Whether to insert a stub definition for an ``"@context"`` property
    #: for each record schema in the generated JSON schema.
    allow_json_ld_context: bool = False

    #: Whether to insert a stub definition for a ``"$schema"`` property for
    #: each record schema in the generated JSON schema.
    allow_json_schema_ref: bool = False

    #: Whether to allow additional properties on JSON records that are not
    #: specified in the schema.
    additional_properties: bool = True