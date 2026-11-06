# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Initial pure-Python implementation of record-spec, covering the feature set
  of the Kotlin `record-spec-lib` and `record-spec-cmd` modules:
  - model core: two-phase schema building, records/mixins/properties/constraints,
    inheritance and mixin composition, validation, events
  - YAML/JSON def-tree serde with a round-trip `SchemaDefBuilder`
  - RDF (rdflib) adapters: parse and serialize schemas in Turtle/N-Triples,
    read/write record *instances* as JSON trees, SHACL/RDFS generation
  - JSON Schema (draft-07) and JSON-LD context generation
  - rdf-mapper template generation
  - import resolution (`BasicSchemaResolver`, `CachingSchemaResolver`,
    `CatalogResolver`)
  - extension records SPI (entry points + programmatic providers)
  - `record-spec` CLI: validate, convert, generate, json-schema, json-ld,
    shacl, rdfs, rdfmapper
  - Upstream parity process: mirror-first policy (ADR-0001), the sync
    checklist (`docs/agents/parity.md`), a weekly parity-watch workflow
    that fails on fixture drift against the Kotlin upstream, and a full
    byte-for-byte mirror of the upstream library test-resources tree

### Fixed (parity with upstream record-spec, Nov 2026)

Each item mirrors the corresponding fix in the upstream Kotlin
implementation, keeping both implementations in lockstep:

- Documentation properties (label/summary/description) are copied when
  records, mixins and properties are cloned, so import resolution and
  merges no longer lose record-level documentation (#58)
- `RecordProperty.remove_constraint(index)` allows removing the first
  constraint (index 0) (#59)
- Creation-time checking of property clashes on records:
  `ShortCodeExistsException` / `PropertyUriExistsException` (#60)
- `Schema.delete_record` raises `RecordReferencedException` when the record
  is referenced from a record property constraint (#61)
- Resolving a relative URI with no base URI in scope raises the typed
  `UriResolutionException` (#62)
- `Record.add_mixin` documentation aligned: duplicate adds have no effect,
  unknown mixin ids are only reported by schema validation (#63)
- Documentation properties are now serialized to and parsed from RDF:
  `RdfBuilder` emits rdfs:label / rdfs:comment / dct:description for
  records, mixins and properties (previously never emitted, and property
  descriptions used rdfs:comment) (#64)
- `JsonSchemaBuilder` honours customized `type_property` and `value_property`
  names instead of hard-coded `@type`/`@value` (#66)
- `RdfRecordReader` accepts `JsonOptions` and honours the configured
  id/type/value/language property names and bare reference ids;
  `RdfRecordWriter`'s structured datatyped-literal dispatch honours
  `type_property` instead of a hard-coded `@type`, making the
  JSON⇄RDF record round trip fully symmetric for customized options (#79)
- Bundled record-spec vocabulary schema: the `repeatable` property declared
  the wrong property URI (`rec:required`); fixed to `rec:repeatable`
- Fixture parity: the two upstream-invalid Turtle fixtures (missing `@prefix`
  terminating `.`) are byte-identical to the upstream fixed versions (#65)

### Notes

- `SchemaValidationException` message formatting appends the individual
  validation errors; intentionally unchanged (cosmetic only, quirk 5)
- rdf-mapper templates map `@type` through `<{@type}>`; by design (quirk 12)