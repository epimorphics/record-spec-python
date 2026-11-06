"""Port of the Kotlin ``JsonSchemaBuilderTests``."""

from __future__ import annotations

import pytest
from helpers import load_json, normalize, resource_path

from record_spec.jsonschema import JsonOptions, JsonSchemaBuilder
from record_spec.model import SchemaBuilder
from record_spec.yaml_parser import YamlParser


def _load_schema(test_name: str):
    with open(resource_path(f"json/{test_name}/schema.yaml")) as f:
        return SchemaBuilder().build(YamlParser().parse(f), None, True)


JSON_SCHEMA_CASES = [
    ("simple", "Foo", "Foo", JsonOptions()),
    ("simple", "Bar", "Bar", JsonOptions()),
    ("simple", "Bar", "Bar.bareRefs", JsonOptions(bare_reference_ids=True)),
    (
        "simple",
        "Bar",
        "Bar.customJsonLdProps",
        JsonOptions(type_property="myType", id_property="myId", value_property="myValue", language_property="myLang"),
    ),
    ("simple", None, "simple_full", JsonOptions()),
    ("simple", "Foo", "Foo_or_Array_Foo", JsonOptions(allow_array=True)),
    ("repeatableProperties", "Foo", "Foo", JsonOptions()),
    ("requiredRepeatableProperties", "Foo", "Foo", JsonOptions()),
    ("patternConstraints", "Foo", "Foo", JsonOptions()),
    ("valueRangeConstraints", "Foo", "Foo", JsonOptions()),
    ("arbitraryLiterals", "Foo", "Foo", JsonOptions()),
    (
        "arbitraryLiterals",
        "Foo",
        "Foo.customJsonLdProps",
        JsonOptions(type_property="myType", value_property="myValue"),
    ),
    ("langStringProperties", "Foo", "Foo", JsonOptions()),
    ("mappedProperties", "Foo", "Foo", JsonOptions()),
    ("jsonLiterals", "Foo", "Foo", JsonOptions()),
    ("nested", "Foo", "Foo", JsonOptions()),
    ("inheritance", "Base", "Base", JsonOptions()),
    ("inheritance", "UsesBase", "UsesBase", JsonOptions()),
]


@pytest.mark.parametrize(
    ("test_name", "record_name", "expected_resource_name", "options"),
    JSON_SCHEMA_CASES,
)
def test_build_json_schema(test_name, record_name, expected_resource_name, options):
    input_schema = _load_schema(test_name)
    input_record = input_schema.resolve_record(record_name) if record_name is not None else None
    builder = JsonSchemaBuilder(options)
    if input_record is not None:
        actual_record_schema = builder.build(input_record)
    else:
        actual_record_schema = builder.build(input_schema, f"{expected_resource_name}.schema.json")

    expected_record_schema = load_json(f"json/{test_name}/{expected_resource_name}.schema.json")
    assert normalize(actual_record_schema) == normalize(expected_record_schema), (
        f"Generated JSON schema does not match json/{test_name}/{expected_resource_name}.schema.json.\n"
        f"actual: {actual_record_schema}\nexpected: {expected_record_schema}"
    )