"""Ports of the Kotlin extension test suites: ``LoaderTests``,
``ExtensionValidationTests``, ``ExtensionSerdeTests`` and the
``getCombinedSchema`` conformance checks."""

from __future__ import annotations

import pytest
import simple_test_service as sts
from helpers import (
    assert_rdf_isomorphic,
    assert_yaml_serialisation,
    load_rdf,
    resource_path,
)

from record_spec.exceptions import (
    InvalidExtensionException,
    InvalidMixinException,
    InvalidPropertyException,
    InvalidRecordException,
    SchemaValidationException,
)
from record_spec.extensions import get_combined_schema, get_extension_service
from record_spec.model import SchemaBuilder
from record_spec.rdf import RdfParser
from record_spec.yaml_parser import YamlParser


@pytest.fixture(autouse=True)
def _registered_service():
    sts.register_simple_service()
    yield
    sts.clear_registered_services()


@pytest.fixture
def load_schema():
    def _load(resource: str):
        path = resource_path(resource)
        with open(path) as f:
            return SchemaBuilder().build(YamlParser().parse(f), None, validate=False)

    return _load


@pytest.fixture
def load_schema_from_rdf():
    def _load(resource: str):
        path = resource_path(resource)
        with open(path, "rb") as f:
            schema_adapter = RdfParser().parse(f, path.as_uri(), "TTL")
        return SchemaBuilder().build(schema_adapter, None, validate=False)

    return _load


def _assert_has_simple_extension(expected_value: str, extensible) -> None:
    records = [ext for ext in extensible.extensions if isinstance(ext, sts.SimpleExtensionRecord)]
    assert any(ext.value == expected_value for ext in records), [ext.value for ext in records]


# ---- LoaderTests ----


def test_loader_can_locate_test_provider():
    service = get_extension_service(sts.SIMPLE_EXTENSION_TYPE)
    assert service is not None
    assert isinstance(service, sts.SimpleTestService)


def test_loader_returns_null_if_service_not_registered():
    sts.clear_registered_services()
    assert get_extension_service(sts.SIMPLE_EXTENSION_TYPE) is None


# ---- combined schema (ExtensionSerdeTests.testCombinedSchemaLoad) ----


def test_combined_schema_load():
    extension_type = "http://epimorphics.com/record-spec/extension/simple"
    combined_schema = get_combined_schema()
    service = get_extension_service(extension_type)
    assert service is not None
    assert any(record.class_uri == extension_type for record in service.schema.records)
    extension_record = next((record for record in combined_schema.records if record.class_uri == extension_type), None)
    assert extension_record is not None
    assert extension_record.get_property("value") is not None


# ---- ExtensionValidationTests ----


def test_schema_extension_validation(load_schema):
    schema = load_schema("extensions/schema_extensions/schema.yaml")
    ext = next(
        (ext for ext in schema.extensions if isinstance(ext, sts.SimpleExtensionRecord)), None
    )
    assert ext is not None
    schema.validate()
    ext.value = "fail"
    with pytest.raises(SchemaValidationException) as exc_info:
        schema.validate()
    assert isinstance(exc_info.value.validation_errors[0], InvalidExtensionException)


def test_mixin_extension_validation(load_schema):
    schema = load_schema("extensions/mixin_extensions/schema.yaml")
    mixin = next(iter(schema.mixins))
    ext = next((ext for ext in mixin.extensions if isinstance(ext, sts.SimpleExtensionRecord)), None)
    assert ext is not None
    schema.validate()
    ext.value = "fail"
    with pytest.raises(SchemaValidationException) as exc_info:
        schema.validate()
    ime = exc_info.value.validation_errors[0]
    assert isinstance(ime, InvalidMixinException)
    assert isinstance(ime.cause, InvalidExtensionException)


def test_record_extension_validation(load_schema):
    schema = load_schema("extensions/record_extensions/schema.yaml")
    record = next(iter(schema.records))
    ext = next(
        (
            ext
            for ext in record.extensions
            if isinstance(ext, sts.SimpleExtensionRecord) and ext.value == "Record Annotation"
        ),
        None,
    )
    assert ext is not None
    schema.validate()
    ext.value = "fail"
    with pytest.raises(SchemaValidationException) as exc_info:
        schema.validate()
    ire = exc_info.value.validation_errors[0]
    assert isinstance(ire, InvalidRecordException)
    assert isinstance(ire.cause, InvalidExtensionException)


def test_property_extension_validation(load_schema):
    schema = load_schema("extensions/property_extensions/schema.yaml")
    record = next(iter(schema.records))
    prop = record.get_property("label")
    assert prop is not None
    ext = next((ext for ext in prop.extensions if isinstance(ext, sts.SimpleExtensionRecord)), None)
    assert ext is not None
    schema.validate()
    ext.value = "fail"
    with pytest.raises(SchemaValidationException) as exc_info:
        schema.validate()
    ire = exc_info.value.validation_errors[0]
    assert isinstance(ire, InvalidRecordException)
    ipe = ire.cause
    assert isinstance(ipe, InvalidPropertyException)
    assert isinstance(ipe.cause, InvalidExtensionException)


# ---- ExtensionSerdeTests (YAML and RDF, incl. round-trip serialisation) ----


def test_schema_extension_serde(load_schema):
    schema = load_schema("extensions/schema_extensions/schema.yaml")
    assert len(list(schema.extensions)) == 1
    _assert_has_simple_extension("Hello World!", schema)
    assert_yaml_serialisation("extensions/schema_extensions/schema.yaml", schema)


def test_schema_extension_rdf_serde(load_schema_from_rdf):
    schema = load_schema_from_rdf("extensions/schema_extensions/schema.ttl")
    assert len(list(schema.extensions)) == 1
    _assert_has_simple_extension("Hello World!", schema)

    # RDF round trip: schema → RDF → schema
    from rdflib import Graph

    from record_spec.rdf import RdfBuilder

    graph = Graph()
    RdfBuilder(graph, "http://example.org/spec/schema").build(schema.adapter)
    expected_graph = load_rdf("extensions/schema_extensions/schema.ttl")
    assert_rdf_isomorphic(expected_graph, graph)


def test_mixin_extension_serde(load_schema):
    schema = load_schema("extensions/mixin_extensions/schema.yaml")
    mixin = next(iter(schema.mixins))
    assert len(list(mixin.extensions)) == 1
    _assert_has_simple_extension("Mixin Annotation", mixin)
    assert_yaml_serialisation("extensions/mixin_extensions/schema.yaml", schema)


def test_mixin_extension_rdf_serde(load_schema_from_rdf):
    schema = load_schema_from_rdf("extensions/mixin_extensions/schema.ttl")
    mixin = next(iter(schema.mixins))
    assert len(list(mixin.extensions)) == 1
    _assert_has_simple_extension("Mixin Annotation", mixin)

    from rdflib import Graph

    from record_spec.rdf import RdfBuilder

    graph = Graph()
    RdfBuilder(graph, "http://example.org/spec/schema").build(schema.adapter)
    expected_graph = load_rdf("extensions/mixin_extensions/schema.ttl")
    assert_rdf_isomorphic(expected_graph, graph)


def test_record_extension_serde(load_schema):
    schema = load_schema("extensions/record_extensions/schema.yaml")
    record = next(iter(schema.records))
    assert len(list(record.extensions)) == 2
    _assert_has_simple_extension("Record Annotation", record)
    _assert_has_simple_extension("Mixin Annotation", record)
    assert_yaml_serialisation("extensions/record_extensions/schema.yaml", schema)


def test_record_extension_rdf_serde(load_schema_from_rdf):
    schema = load_schema_from_rdf("extensions/record_extensions/schema.ttl")
    record = next(iter(schema.records))
    assert len(list(record.extensions)) == 2
    _assert_has_simple_extension("Record Annotation", record)
    _assert_has_simple_extension("Mixin Annotation", record)

    from rdflib import Graph

    from record_spec.rdf import RdfBuilder

    graph = Graph()
    RdfBuilder(graph, "http://example.org/spec/schema").build(schema.adapter)
    expected_graph = load_rdf("extensions/record_extensions/schema.ttl")
    assert_rdf_isomorphic(expected_graph, graph)


def test_property_extension_serde(load_schema):
    schema = load_schema("extensions/property_extensions/schema.yaml")
    record = next(iter(schema.records))
    prop = record.get_property("label")
    assert prop is not None
    assert len(list(prop.extensions)) == 1
    _assert_has_simple_extension("Property Annotation", prop)
    assert_yaml_serialisation("extensions/property_extensions/schema.yaml", schema)


def test_property_extension_rdf_serde(load_schema_from_rdf):
    schema = load_schema_from_rdf("extensions/property_extensions/schema.ttl")
    record = next(iter(schema.records))
    prop = record.get_property("label")
    assert prop is not None
    assert len(list(prop.extensions)) == 1
    _assert_has_simple_extension("Property Annotation", prop)

    from rdflib import Graph

    from record_spec.rdf import RdfBuilder

    graph = Graph()
    RdfBuilder(graph, "http://example.org/spec/schema").build(schema.adapter)
    expected_graph = load_rdf("extensions/property_extensions/schema.ttl")
    assert_rdf_isomorphic(expected_graph, graph)