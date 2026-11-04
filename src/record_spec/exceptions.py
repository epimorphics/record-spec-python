"""The record-spec exception hierarchy."""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from record_spec.model import Mixin, Property, PropertyMapping, Record, RecordProperty


class RecordSpecException(Exception):
    """Base class for all record-spec exceptions."""

    def __init__(self, message: str | None = None, cause: Exception | None = None):
        super().__init__(message)
        #: The underlying exception that caused this one, if any.
        self.cause: Exception | None = cause

    @property
    def message(self) -> str:
        """The message of this exception."""
        return str(self)


class SchemaValidationException(RecordSpecException):
    """Raised when schema validation fails; carries the individual validation errors."""

    def __init__(self, validation_errors: Iterable[Exception]):
        self.validation_errors = list(validation_errors)
        super().__init__("Schema validation failed")

    @property
    def message(self) -> str:
        return super().__str__() + "\n\t" + "\n\t".join(str(e) for e in self.validation_errors)

    def __str__(self) -> str:
        return self.message


class SchemaReadException(RecordSpecException):
    """Raised when a schema cannot be read or parsed."""

    def __init__(self, message: str, cause: Exception | None = None):
        super().__init__(message)
        self.cause = cause


class RecordExistsException(RecordSpecException):
    """Raised when creating a record with an id or short-code that already exists."""

    def __init__(self, attribute_name: str, attribute_value: str):
        self.attribute_name = attribute_name
        self.attribute_value = attribute_value
        super().__init__(f"A record with {attribute_name} = {attribute_value} already exists in the schema.")


class RecordNotFoundException(RecordSpecException):
    """Raised when a record cannot be resolved by id, short-code or class URI."""

    def __init__(self, message: str):
        super().__init__(message)


class RecordReferencedException(RecordSpecException):
    """Raised when attempting to delete a record that is referenced by other schema elements."""

    def __init__(self, record_id: str):
        super().__init__(f"The record with ID {record_id} is referenced by one or more records.")


class RecordShortCodeClashException(RecordSpecException):
    """Raised when two records with different ids share the same short-code."""

    def __init__(self, record: Record, existing_record_id: str, existing_record_short_code: str):
        self.record = record
        super().__init__(
            "Record short-code clash detected. "
            f"A record with id '{record.id}' and shortCode '{record.short_code}' clashes with an existing "
            f"record with id '{existing_record_id}' and shortCode '{existing_record_short_code}'."
        )


class RecordClassUriClashException(RecordSpecException):
    """Raised when two records with the same id have different class URIs."""

    def __init__(self, record: Record, existing_record_id: str, existing_record_class_uri: str):
        self.record = record
        super().__init__(
            "Record class URI clash detected. "
            f"A record with id '{record.id}' and class URI '{record.class_uri}' clashes with an existing "
            f"record with id '{existing_record_id}' and shortCode '{existing_record_class_uri}'."
        )


class RecordParentClashException(RecordSpecException):
    """Raised when merging a record with an existing record that has a different parent."""

    def __init__(self, clash_id: str, existing_parent: str | None, other_parent: str | None):
        super().__init__(
            "Record parent clash detected. "
            f"A record with id '{clash_id}' and parent '{other_parent}' clashes with an existing record "
            f"with the same id but a different parent '{existing_parent}'."
        )


class CircularInheritanceException(RecordSpecException):
    """Raised when a circular inheritance chain is detected."""

    def __init__(self, path: list[Record]):
        self.path = path
        super().__init__("A cyclic inheritance was found.")

    def __str__(self) -> str:
        return super().__str__() + " -> ".join(r.id for r in self.path)


class PropertyClashException(RecordSpecException):
    """Raised when two properties clash in short-code or URI but not both."""

    def __init__(self, property_a: Property, property_b: Property):
        self.property_a = property_a
        self.property_b = property_b
        super().__init__(f"Clash between property {property_a} and property {property_b}.")


class MixinPropertyClashException(RecordSpecException):
    """Raised when two mixins used by the same record define clashing properties."""

    def __init__(self, clash_property: str, clash_value: str, mixin_a: Mixin, mixin_b: Mixin):
        self.clash_property = clash_property
        self.clash_value = clash_value
        self.mixin_a = mixin_a
        self.mixin_b = mixin_b
        super().__init__()

    def __str__(self) -> str:
        return (
            f"Mixin {self.mixin_a.id} and Mixin {self.mixin_b.id} both define a property with "
            f"{self.clash_property} = {self.clash_value} and cannot be combined on the same record."
        )


class MixinExistsException(RecordSpecException):
    """Raised when creating a mixin with an id that already exists."""

    def __init__(self, mixin_id: str):
        super().__init__(f"A mixin with id {mixin_id} already exists.")


class MixinNotFoundException(RecordSpecException):
    """Raised when a mixin cannot be resolved by id."""

    def __init__(self, message: str):
        super().__init__(message)


class MixinReferencedException(RecordSpecException):
    """Raised when attempting to delete a mixin that is referenced by a record."""

    def __init__(self, mixin_id: str):
        super().__init__(f"The mixin {mixin_id} is referenced by one or more records.")


class IncompatiblePropertyException(RecordSpecException):
    """Raised when two properties cannot be combined during inheritance."""

    def __init__(self, property_a: Property, property_b: Property, reason: str, cause: Exception | None = None):
        self.property_a = property_a
        self.property_b = property_b
        super().__init__(f"Incompatible properties {property_a} and {property_b}. {reason}", cause)


class IncompatibleRangeException(RecordSpecException):
    """Raised when the ranges of two properties have no compatible overlap."""

    def __init__(self, message: str):
        super().__init__(message)


class IncompatiblePropertyMapsException(RecordSpecException):
    """Raised when two property maps specify different key properties."""

    def __init__(self, map_a: PropertyMapping, map_b: PropertyMapping):
        super().__init__(
            f"Property maps {map_a} and {map_b} cannot be combined "
            "as they specify different key and/or value properties."
        )


class InvalidRecordException(RecordSpecException):
    """Raised when a record fails validation."""

    def __init__(self, record: Record, cause: RecordSpecException):
        self.record = record
        detail = cause.message if hasattr(cause, "message") else cause
        super().__init__(f"Invalid record: {record.id}.\n\tCause: {detail}", cause)


class InvalidPropertyException(RecordSpecException):
    """Raised when a property fails validation."""

    def __init__(self, prop: Property, cause: RecordSpecException):
        self.property = prop
        detail = cause.message if hasattr(cause, "message") else cause
        super().__init__(
            f"Invalid property {prop.short_code} ({prop.property_uri}):\n\tCause: {detail}",
            cause,
        )


class InvalidPropertyMapException(RecordSpecException):
    """Raised when a property map is invalid for the property it is declared on."""

    def __init__(self, prop: RecordProperty, property_mapping: PropertyMapping, reason: str):
        self.property = prop
        self.property_mapping = property_mapping
        super().__init__(f"Invalid property map {property_mapping}: {reason}")


class InvalidLiteralConstraintException(RecordSpecException):
    """Raised when a literal constraint is invalid."""

    def __init__(self, message: str):
        super().__init__(message)


class InvalidRecordConstraintException(RecordSpecException):
    """Raised when a record constraint is invalid (e.g. its record reference does not resolve)."""

    def __init__(self, message: str, cause: Exception | None = None):
        super().__init__(message, cause)


class InvalidMixinException(RecordSpecException):
    """Raised when a mixin fails validation."""

    def __init__(self, mixin: Mixin, cause: RecordSpecException):
        self.mixin = mixin
        detail = cause.message if hasattr(cause, "message") else cause
        super().__init__(f"Invalid mixin: {mixin.id}.\n\tCause: {detail}", cause)


class InvalidShortCodeException(RecordSpecException):
    """Raised when a short-code does not match the required syntax."""

    def __init__(self, short_code: str):
        super().__init__(f"The shortCode value is invalid: {short_code}")


class NoComparatorException(RecordSpecException):
    """Raised when comparing values of a datatype with no registered comparator."""

    def __init__(self, datatype: str):
        self.datatype = datatype
        super().__init__(f"No comparator available to compare values of datatype {datatype}.")


class InvalidReversePropertyRangeException(RecordSpecException):
    """Raised when a reversed property's range is incompatible with the corresponding forward property."""

    def __init__(self, message: str):
        super().__init__(message)


class InvalidExtensionException(RecordSpecException):
    """Raised when an extension record fails validation."""

    def __init__(self, message: str, cause: Exception | None = None):
        super().__init__(message, cause)


class RdfRecordReaderException(RecordSpecException):
    """Raised when reading an RDF resource as a record fails."""

    def __init__(self, message: str):
        super().__init__(message)


class RdfRecordWriterException(RecordSpecException):
    """Raised when writing record data as RDF fails."""

    def __init__(self, message: str):
        super().__init__(message)


class RdfParserException(RecordSpecException):
    """Raised when parsing an RDF serialization of a schema fails."""

    def __init__(self, message: str):
        super().__init__(message)


class RdfBuilderException(RecordSpecException):
    """Raised when building an RDF model of a schema fails."""

    def __init__(self, message: str):
        super().__init__(message)