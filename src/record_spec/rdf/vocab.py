"""The record-spec RDF vocabulary constants (the Kotlin ``Vocab`` object)."""

from __future__ import annotations

RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
RDF_TYPE = RDF + "type"

REC = "http://vocab.epimorphics.com/record-spec/def/"

REC_SCHEMA = REC + "Schema"
REC_RECORD = REC + "Record"
REC_MIXIN_CLASS = REC + "Mixin"
REC_LITERAL_PROPERTY = REC + "LiteralProperty"
REC_RECORD_PROPERTY = REC + "RecordProperty"
REC_LITERAL_CONSTRAINT = REC + "LiteralConstraint"
REC_RECORD_CONSTRAINT = REC + "RecordConstraint"

REC_CONSTRAINT = REC + "constraint"
REC_DATATYPE = REC + "datatype"
REC_EXTENDS = REC + "extends"
REC_EXTENSION = REC + "extension"
REC_IDENTIFIER = REC + "identifier"
REC_IMPLEMENTS = REC + "implements"
REC_IMPORTS = REC + "imports"
REC_IN = REC + "in"
REC_KEY_PROPERTY = REC + "keyProperty"
REC_MAX_EXCLUSIVE = REC + "maxExclusive"
REC_MAX_INCLUSIVE = REC + "maxInclusive"
REC_MIN_EXCLUSIVE = REC + "minExclusive"
REC_MIN_INCLUSIVE = REC + "minInclusive"
REC_MIXIN = REC + "mixin"
REC_NESTED = REC + "nested"
REC_PATTERN = REC + "pattern"
REC_PROPERTY = REC + "property"
REC_PROPERTY_MAP = REC + "propertyMap"
REC_PREFIX = REC + "prefix"
REC_PREFIX_MAPPING = REC + "prefixMapping"
REC_RECORD_PREDICATE = REC + "record"
REC_REPEATABLE = REC + "repeatable"
REC_REQUIRED = REC + "required"
REC_REVERSED = REC + "reversed"
REC_SHORT_CODE = REC + "shortCode"
REC_URI = REC + "uri"
REC_VALUE_PROPERTY = REC + "valueProperty"

RDFS = "http://www.w3.org/2000/01/rdf-schema#"
RDFS_LABEL = RDFS + "label"
RDFS_COMMENT = RDFS + "comment"

DCT = "http://purl.org/dc/terms/"
DCT_DESCRIPTION = DCT + "description"


class Vocab:
    """Convenience holder mapping the vocabulary constants to rdflib terms."""

    rdf_type = RDF_TYPE

    rec_schema = REC_SCHEMA
    rec_record_class = REC_RECORD
    rec_mixin_class = REC_MIXIN_CLASS
    rec_literal_property = REC_LITERAL_PROPERTY
    rec_record_property = REC_RECORD_PROPERTY
    rec_literal_constraint = REC_LITERAL_CONSTRAINT
    rec_record_constraint = REC_RECORD_CONSTRAINT

    rec_constraint = REC_CONSTRAINT
    rec_datatype = REC_DATATYPE
    rec_extends = REC_EXTENDS
    rec_extension = REC_EXTENSION
    rec_identifier = REC_IDENTIFIER
    rec_implements = REC_IMPLEMENTS
    rec_imports = REC_IMPORTS
    rec_in = REC_IN
    rec_key_property = REC_KEY_PROPERTY
    rec_max_exclusive = REC_MAX_EXCLUSIVE
    rec_max_inclusive = REC_MAX_INCLUSIVE
    rec_min_exclusive = REC_MIN_EXCLUSIVE
    rec_min_inclusive = REC_MIN_INCLUSIVE
    rec_mixin = REC_MIXIN
    rec_nested = REC_NESTED
    rec_pattern = REC_PATTERN
    rec_property = REC_PROPERTY
    rec_property_map = REC_PROPERTY_MAP
    rec_prefix = REC_PREFIX
    rec_prefix_mapping = REC_PREFIX_MAPPING
    rec_record_predicate = REC_RECORD_PREDICATE
    rec_repeatable = REC_REPEATABLE
    rec_required = REC_REQUIRED
    rec_reversed = REC_REVERSED
    rec_short_code = REC_SHORT_CODE
    rec_uri = REC_URI
    rec_value_property = REC_VALUE_PROPERTY

    rdfs_label = RDFS_LABEL
    rdfs_comment = RDFS_COMMENT
    dct_description = DCT_DESCRIPTION