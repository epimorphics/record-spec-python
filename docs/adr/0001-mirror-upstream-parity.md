# ADR-0001: Keep record-spec-python in lockstep with the Kotlin record-spec

**Status:** accepted
**Date:** 2026-11-06

## Context

`record-spec-python` is a deliberate, feature-complete translation of the
Kotlin `record-spec` implementation (`epimorphics/record-spec`). The port's
value depends on the two implementations agreeing: a schema, validation
error, JSON Schema, JSON-LD context, SHACL shape, rdf-mapper template or
RDF serialization produced by one must match the other.

During the M1–M7 port we recorded twelve behavioural "quirks" of the
Kotlin implementation and mirrored each faithfully rather than fixing
unilaterally. The subsequent upstream review resolved them as issues
#58–#66 and #79; every fix was then ported here with its tests and
fixtures. That cycle demonstrated both halves of the policy:

- Unilateral Python-side fixes would silently fork the implementations.
- Manual drift detection fails: upstream fixes were only discovered when
  explicitly looked for.

## Decision

**Mirror-first parity.** The Python implementation tracks the Kotlin
upstream; the direction of change is upstream → Python, never the reverse.

1. **Mirror first.** Never fix a Python-side divergence ahead of upstream.
   When a divergence is found, record it in a `.scratch` ticket (see
   `docs/agents/issue-tracker.md`), optionally raise it upstream, and port
   the fix when upstream decides. The only exception: fixes *upstream has
   already made* are ported promptly.
2. **Fixture byte-parity.** `tests/resources` mirrors the upstream
   `record-spec-lib/src/test/resources` tree (excluding `META-INF`)
   byte-for-byte. Fixture fixes are made upstream and re-copied, never
   patched locally.
3. **Test-name fidelity.** Upstream test names are ported verbatim, even
   when odd (e.g. two `RdfRecordTests` names that describe the opposite
   direction to what they exercise), so the suites stay diffable.
4. **Commit convention.** One upstream change = one Python commit,
   titled `Port upstream #NNN: <upstream title>`, mapping the upstream
   commit hash in the body, backed by one tracker ticket.
5. **Automated drift detection.** A scheduled `parity-watch` workflow
   byte-diffs the mirrored fixture tree and reports upstream commits
   since the last synced marker (`.parity-upstream-sha`); fixture drift
   fails the workflow loudly.

The operational procedure (how to perform a sync) lives in
`docs/agents/parity.md`.

## Consequences

- Any behavioural difference between the implementations is, by
  definition, a bug in one of them; the tracker records which side
  should change.
- The Python suite can act as a conformance harness for upstream changes:
  a ported change that breaks Python tests indicates an upstream
  regression worth raising.
- New upstream features must be ported before this implementation can
  claim feature parity; the parity watch surfaces them.
- `.parity-upstream-sha` is advanced only by a completed sync, so the
  informational report can lag reality without masking fixture drift
  (the byte-diff is the source of truth).