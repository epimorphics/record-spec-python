# record-spec-python

A pure-Python implementation of [record-spec](https://github.com/epimorphics/record-spec):
a schema language for defining record-like views of RDF data.

This is a feature-complete port of the Kotlin `record-spec-lib` and `record-spec-cmd`
modules (the `record-spec-aml` module is out of scope). Semantics are 1:1 with the
Kotlin implementation; the API is idiomatic Python.

## Layout

- `src/record_spec/model/` — the core model: `Schema`, `Record`, `Mixin`, properties,
  constraints, validation, events, and the inheritance/mixin-composition algorithms.
- `src/record_spec/serde/` — YAML/JSON def-tree serialization/deserialization.
- `src/record_spec/convert.py` — the read-side adapter interfaces used by
  `SchemaBuilder` to build a `Schema` from any source format.
- `src/record_spec/values/` — datatype comparators and CURI resolution.
- `src/record_spec/exceptions.py` — the exception hierarchy.

## Development

```bash
uv sync
uv run pytest
uv run mypy
uv run ruff check
```