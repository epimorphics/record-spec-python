"""Model-spec generation: convert a record-spec schema into a model-spec definition (YAML)."""

from record_spec.modelspec.builder import ModelSpecBuilder
from record_spec.modelspec.model_def import ClassDef, ModelDef, PropertyDef, PropertyType
from record_spec.modelspec.options import ModelSpecOptions

__all__ = [
    "ModelSpecBuilder",
    "ModelSpecOptions",
    "ModelDef",
    "ClassDef",
    "PropertyDef",
    "PropertyType",
]
