"""Port of the Kotlin ``ModelSpecBuilderTests``.

Ported from model-spec's RecordSpecAdapterTest, adapted to assert on the
ModelSpecBuilder model-def output.
"""

from __future__ import annotations

import pytest
import yaml
from helpers import load_schema, resource_path

from record_spec.modelspec import ModelDef, ModelSpecBuilder, ModelSpecOptions, PropertyType


def _build(include_mixins: bool = False, type_property: str = "@type") -> ModelDef:
    schema = load_schema("modelspec/spec.yaml")
    return ModelSpecBuilder(ModelSpecOptions(include_mixins=include_mixins, type_property=type_property)).build(schema)


def _to_set(types: list[str] | None) -> set[str] | None:
    """The Kotlin ``types?.toSet()``."""
    return set(types) if types is not None else None


def _yaml_equivalent(expected: str, actual: str) -> bool:
    """Compare two YAML documents as trees, ignoring formatting differences."""
    return yaml.safe_load(expected) == yaml.safe_load(actual)


class TestWithoutMixins:
    @pytest.fixture
    def model(self) -> ModelDef:
        return _build()

    def test_schema(self, model: ModelDef) -> None:
        assert model.prefixes == {
            "c": "http://vocab.epimorphics.com/agora/def/catalog/",
            "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
            "owl": "http://www.w3.org/2002/07/owl#",
            "u": "http://vocab.epimorphics.com/agora/def/upper/",
            "xsd": "http://www.w3.org/2001/XMLSchema#",
            "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
            "dc": "http://purl.org/dc/elements/1.1/",
        }
        assert model.comment == "A subset of the Agora Catalog data model, adapted for testing purposes."

    def test_records(self, model: ModelDef) -> None:
        # classes sorted by URI: c:CatalogRecord, c:Dataset, c:Distribution, u:Agent, u:Thing
        classes = model.classes
        assert len(classes) == 5

        catalog_record = classes[0]
        assert catalog_record.uri == "http://vocab.epimorphics.com/agora/def/catalog/CatalogRecord"
        assert catalog_record.name == "CatalogRecord"
        assert catalog_record.comment == "A curated collection of metadata about resources (ref: DCAT)."
        assert catalog_record.sub_class_of == []
        assert catalog_record.scheme is None
        assert catalog_record.value_base is None
        assert catalog_record.polymorphic is False
        # properties sorted by URI: u:contributor, u:primaryTopic, u:published, rdf:type
        assert len(catalog_record.properties) == 4
        contributor = catalog_record.properties[0]
        assert contributor.uri == "http://vocab.epimorphics.com/agora/def/upper/contributor"
        assert contributor.name == "contributor"
        assert contributor.kind is PropertyType.OBJECT
        assert _to_set(contributor.types) == {"http://vocab.epimorphics.com/agora/def/upper/Agent"}
        assert contributor.multi is True
        assert contributor.optional is True
        assert contributor.unique is False
        assert contributor.comment == "Zero or more contributors to a publication"
        primary_topic = catalog_record.properties[1]
        assert primary_topic.uri == "http://vocab.epimorphics.com/agora/def/upper/primaryTopic"
        assert primary_topic.name == "primaryTopic"
        assert primary_topic.kind is PropertyType.OBJECT
        assert _to_set(primary_topic.types) == {"http://vocab.epimorphics.com/agora/def/catalog/Dataset"}
        assert primary_topic.multi is False
        assert primary_topic.optional is False
        assert primary_topic.comment == "The primary topic of some descriptive document or record."
        published = catalog_record.properties[2]
        assert published.uri == "http://vocab.epimorphics.com/agora/def/upper/published"
        assert published.name == "published"
        assert published.kind is PropertyType.DATATYPE
        assert _to_set(published.types) == {
            "http://www.w3.org/2001/XMLSchema#date",
            "http://www.w3.org/2001/XMLSchema#dateTime",
        }
        assert published.multi is False
        assert published.optional is True
        assert published.comment == "Date or date time of publication."
        rdf_type = catalog_record.properties[3]
        assert rdf_type.uri == "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
        assert rdf_type.name == "@type"
        assert rdf_type.multi is True
        assert rdf_type.optional is True
        assert rdf_type.unique is False

        dataset = classes[1]
        assert dataset.uri == "http://vocab.epimorphics.com/agora/def/catalog/Dataset"
        assert dataset.name == "Dataset"
        assert dataset.comment == "A collection of data, published or curated by a single agent."
        assert dataset.sub_class_of == ["http://vocab.epimorphics.com/agora/def/upper/Thing"]
        assert dataset.polymorphic is False
        # properties sorted by URI: c:distribution, u:description, u:prefLabel, rdf:type
        assert len(dataset.properties) == 4
        distribution_prop = dataset.properties[0]
        assert distribution_prop.uri == "http://vocab.epimorphics.com/agora/def/catalog/distribution"
        assert distribution_prop.name == "distribution"
        assert distribution_prop.kind is PropertyType.OBJECT
        assert _to_set(distribution_prop.types) == {"http://vocab.epimorphics.com/agora/def/catalog/Distribution"}
        assert distribution_prop.multi is True
        assert distribution_prop.optional is True
        assert distribution_prop.comment is None
        description_prop = dataset.properties[1]
        assert description_prop.uri == "http://vocab.epimorphics.com/agora/def/upper/description"
        assert description_prop.name == "description"
        assert description_prop.kind is PropertyType.DATATYPE
        assert _to_set(description_prop.types) == {
            "http://www.w3.org/2001/XMLSchema#string",
            "http://www.w3.org/1999/02/22-rdf-syntax-ns#langString",
        }
        assert description_prop.multi is True
        assert description_prop.optional is True
        assert description_prop.comment == (
            "A (long) description of something, this may extend over several sentences or paragraphs."
        )
        pref_label = dataset.properties[2]
        assert pref_label.uri == "http://vocab.epimorphics.com/agora/def/upper/prefLabel"
        assert pref_label.name == "prefLabel"
        assert pref_label.kind is PropertyType.DATATYPE
        assert _to_set(pref_label.types) == {"http://www.w3.org/1999/02/22-rdf-syntax-ns#langString"}
        assert pref_label.multi is False
        assert pref_label.optional is False
        assert pref_label.comment == "multi-lingual preferred label"
        rdf_type = dataset.properties[3]
        assert rdf_type.uri == "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
        assert rdf_type.name == "@type"

        distribution = classes[2]
        assert distribution.uri == "http://vocab.epimorphics.com/agora/def/catalog/Distribution"
        assert distribution.name == "Distribution"
        assert distribution.comment == "An accessible or downloadable copy of a dataset or document."
        assert distribution.sub_class_of == []
        assert distribution.polymorphic is False
        # properties sorted by URI: c:byteSize, c:mediaType, rdf:type
        assert len(distribution.properties) == 3
        byte_size = distribution.properties[0]
        assert byte_size.uri == "http://vocab.epimorphics.com/agora/def/catalog/byteSize"
        assert byte_size.name == "byteSize"
        assert byte_size.kind is PropertyType.DATATYPE
        assert _to_set(byte_size.types) == {"http://www.w3.org/2001/XMLSchema#integer"}
        assert byte_size.multi is False
        assert byte_size.optional is True
        assert byte_size.comment == "raw (uncompressed) size of a distribution in bytes."
        media_type = distribution.properties[1]
        assert media_type.uri == "http://vocab.epimorphics.com/agora/def/catalog/mediaType"
        assert media_type.name == "mediaType"
        assert media_type.kind is PropertyType.OBJECT
        assert media_type.types is None
        assert media_type.multi is False
        assert media_type.optional is False
        assert media_type.comment == "The internet media type of a distribution."
        rdf_type = distribution.properties[2]
        assert rdf_type.uri == "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
        assert rdf_type.name == "@type"

        agent = classes[3]
        assert agent.uri == "http://vocab.epimorphics.com/agora/def/upper/Agent"
        assert agent.name == "Agent"
        assert agent.comment == "Encompasses both human/organisational entities."
        assert agent.sub_class_of == ["http://vocab.epimorphics.com/agora/def/upper/Thing"]
        assert agent.polymorphic is False
        # properties sorted by URI: u:description, u:prefLabel, rdf:type
        assert len(agent.properties) == 3
        description_prop = agent.properties[0]
        assert description_prop.uri == "http://vocab.epimorphics.com/agora/def/upper/description"
        assert description_prop.name == "description"
        assert description_prop.kind is PropertyType.DATATYPE
        assert _to_set(description_prop.types) == {
            "http://www.w3.org/2001/XMLSchema#string",
            "http://www.w3.org/1999/02/22-rdf-syntax-ns#langString",
        }
        assert description_prop.multi is True
        assert description_prop.optional is True
        assert description_prop.comment == (
            "A (long) description of something, this may extend over several sentences or paragraphs."
        )
        pref_label = agent.properties[1]
        assert pref_label.uri == "http://vocab.epimorphics.com/agora/def/upper/prefLabel"
        assert pref_label.name == "prefLabel"
        assert pref_label.kind is PropertyType.DATATYPE
        assert _to_set(pref_label.types) == {"http://www.w3.org/1999/02/22-rdf-syntax-ns#langString"}
        assert pref_label.multi is False
        assert pref_label.optional is False
        assert pref_label.comment == "multi-lingual preferred label"
        rdf_type = agent.properties[2]
        assert rdf_type.uri == "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
        assert rdf_type.name == "@type"

        thing = classes[4]
        assert thing.uri == "http://vocab.epimorphics.com/agora/def/upper/Thing"
        assert thing.name == "Thing"
        assert thing.comment is None
        assert thing.sub_class_of == []
        assert thing.polymorphic is True
        # properties sorted by URI: u:description, u:prefLabel, rdf:type
        assert len(thing.properties) == 3
        description_prop = thing.properties[0]
        assert description_prop.uri == "http://vocab.epimorphics.com/agora/def/upper/description"
        assert description_prop.name == "description"
        assert description_prop.kind is PropertyType.DATATYPE
        assert description_prop.multi is True
        assert description_prop.optional is True
        assert description_prop.comment == (
            "A (long) description of something, this may extend over several sentences or paragraphs."
        )
        pref_label = thing.properties[1]
        assert pref_label.uri == "http://vocab.epimorphics.com/agora/def/upper/prefLabel"
        assert pref_label.name == "prefLabel"
        assert pref_label.kind is PropertyType.DATATYPE
        assert _to_set(pref_label.types) == {"http://www.w3.org/1999/02/22-rdf-syntax-ns#langString"}
        assert pref_label.multi is False
        assert pref_label.optional is False
        assert pref_label.comment == "multi-lingual preferred label"
        rdf_type = thing.properties[2]
        assert rdf_type.uri == "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
        assert rdf_type.name == "@type"


class TestWithMixins:
    @pytest.fixture
    def model(self) -> ModelDef:
        return _build(include_mixins=True)

    def test_records(self, model: ModelDef) -> None:
        # classes sorted by name: Agent, CatalogRecord, Dataset, Distribution, Thing, WithPublicationData
        classes = sorted(model.classes, key=lambda cls: cls.name)
        assert len(classes) == 6

        agent = classes[0]
        assert agent.uri == "http://vocab.epimorphics.com/agora/def/upper/Agent"
        assert agent.sub_class_of == ["http://vocab.epimorphics.com/agora/def/upper/Thing"]
        assert len(agent.properties) == 3

        catalog_record = classes[1]
        assert catalog_record.uri == "http://vocab.epimorphics.com/agora/def/catalog/CatalogRecord"
        assert catalog_record.name == "CatalogRecord"
        assert catalog_record.comment == "A curated collection of metadata about resources (ref: DCAT)."
        # mixin reference is not a compactable URI so is emitted in full
        assert catalog_record.sub_class_of == ["http://vocab.epimorphics.com/agora/def/WithPublicationData"]
        assert catalog_record.polymorphic is False
        assert len(catalog_record.properties) == 4
        contributor = catalog_record.properties[0]
        assert contributor.uri == "http://vocab.epimorphics.com/agora/def/upper/contributor"
        assert contributor.name == "contributor"
        assert contributor.kind is PropertyType.OBJECT
        assert _to_set(contributor.types) == {"http://vocab.epimorphics.com/agora/def/upper/Agent"}
        assert contributor.multi is True
        assert contributor.optional is True
        assert contributor.comment == "Zero or more contributors to a publication"
        published = catalog_record.properties[2]
        assert published.uri == "http://vocab.epimorphics.com/agora/def/upper/published"
        assert published.name == "published"
        assert published.kind is PropertyType.DATATYPE
        assert _to_set(published.types) == {
            "http://www.w3.org/2001/XMLSchema#date",
            "http://www.w3.org/2001/XMLSchema#dateTime",
        }
        rdf_type = catalog_record.properties[3]
        assert rdf_type.uri == "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
        assert rdf_type.name == "@type"

        dataset = classes[2]
        assert dataset.uri == "http://vocab.epimorphics.com/agora/def/catalog/Dataset"
        assert dataset.sub_class_of == ["http://vocab.epimorphics.com/agora/def/upper/Thing"]
        assert len(dataset.properties) == 4

        distribution = classes[3]
        assert distribution.uri == "http://vocab.epimorphics.com/agora/def/catalog/Distribution"
        assert distribution.sub_class_of == []
        assert len(distribution.properties) == 3

        thing = classes[4]
        assert thing.uri == "http://vocab.epimorphics.com/agora/def/upper/Thing"
        assert thing.sub_class_of == []
        assert len(thing.properties) == 3

        with_publication_data = classes[5]
        assert with_publication_data.uri == "http://vocab.epimorphics.com/agora/def/WithPublicationData"
        assert with_publication_data.name == "WithPublicationData"
        assert with_publication_data.comment == (
            "WithPublicationData: a mix-in class for attributing publication data to some (published) thing."
        )
        assert with_publication_data.sub_class_of == []
        assert with_publication_data.polymorphic is False
        assert len(with_publication_data.properties) == 3
        contributor = with_publication_data.properties[0]
        assert contributor.uri == "http://vocab.epimorphics.com/agora/def/upper/contributor"
        assert contributor.name == "contributor"
        assert contributor.kind is PropertyType.OBJECT
        assert _to_set(contributor.types) == {"http://vocab.epimorphics.com/agora/def/upper/Agent"}
        assert contributor.multi is True
        assert contributor.optional is True
        assert contributor.comment == "Zero or more contributors to a publication"
        published = with_publication_data.properties[1]
        assert published.uri == "http://vocab.epimorphics.com/agora/def/upper/published"
        assert published.name == "published"
        assert published.kind is PropertyType.DATATYPE
        assert _to_set(published.types) == {
            "http://www.w3.org/2001/XMLSchema#date",
            "http://www.w3.org/2001/XMLSchema#dateTime",
        }
        rdf_type = with_publication_data.properties[2]
        assert rdf_type.uri == "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
        assert rdf_type.name == "@type"


class TestTypeProperty:
    def test_custom_type_property_name(self) -> None:
        model = _build(type_property="type")
        thing = next(cls for cls in model.classes if cls.name == "Thing")
        type_prop = next(prop for prop in thing.properties if prop.uri == "http://www.w3.org/1999/02/22-rdf-syntax-ns#type")
        assert type_prop.name == "type"


class TestGoldenOutput:
    def test_golden_output(self) -> None:
        with open(resource_path("modelspec/golden/spec.yaml")) as f:
            golden = f.read()
        schema = load_schema("modelspec/spec.yaml")
        yaml_text = ModelSpecBuilder(ModelSpecOptions()).write_yaml(schema)
        assert _yaml_equivalent(golden, yaml_text)

    def test_golden_output_with_mixins(self) -> None:
        with open(resource_path("modelspec/golden/spec-with-mixins.yaml")) as f:
            golden = f.read()
        schema = load_schema("modelspec/spec.yaml")
        yaml_text = ModelSpecBuilder(ModelSpecOptions(include_mixins=True)).write_yaml(schema)
        assert _yaml_equivalent(golden, yaml_text)
