# Parity process: syncing with the Kotlin upstream

This implementation is a deliberate mirror of the Kotlin `record-spec`
(`epimorphics/record-spec`). The policy and rationale are in
[ADR-0001](../adr/0001-mirror-upstream-parity.md); this document is the
operational checklist for performing a sync.

## Detecting drift

- The **parity-watch** workflow (`.github/workflows/parity-watch.yaml`)
  runs weekly and on manual dispatch. It fails if any file in the
  mirrored fixture tree differs from upstream, and prints upstream
  commits since the last synced marker.
- A red parity-watch (or an upstream change noticed manually) opens a
  `.scratch` ticket per the [issue tracker](issue-tracker.md)
  conventions, then this procedure is executed.

## The sync checklist

1. **Locate the upstream change.** The upstream repo is usually at
   `/home/kal/Projects/record-spec` (otherwise clone
   `epimorphics/record-spec`). Find the commit(s) of interest:
   `git log --oneline` and `git show <hash>` for the diff, including its
   tests and fixtures.
2. **Open a tracker ticket** in
   `.scratch/record-spec-python-port/issues/` (next available number,
   `Status: needs-triage`) describing the divergence or new feature and
   the upstream commit that resolves it. Skip if a ticket already exists.
3. **Port the source change.** Mirror the upstream semantics exactly —
   translate, don't redesign. Preserve upstream doc-comment intent and
   any `#NNN` issue references in comments.
4. **Re-sync fixtures.** Copy every upstream test-resource file touched
   by the change from
   `record-spec-lib/src/test/resources/` into `tests/resources/`
   byte-for-byte. Never patch a fixture locally; if a fixture is wrong,
   it gets fixed upstream and re-copied.
5. **Port the tests verbatim.** Same test names as upstream (even odd
   ones), same assertions. New test classes go in `tests/` as
   `test_<name>.py` following the existing ported suites.
6. **Verify.** `uv run pytest`, `uv run mypy`, `uv run ruff check src
   tests` — all must be clean. Then verify full fixture byte-parity (see
   the verification snippet below).
7. **Advance the marker.** `git -C /path/to/record-spec rev-parse HEAD >
   .parity-upstream-sha` (only after a completed sync).
8. **Commit** as `Port upstream #NNN: <upstream title>`, with the
   upstream commit hash in the body and the tracker ticket updated to
   `Status: resolved`. Update `CHANGELOG.md` under the relevant issue
   number.
9. **Push.** CI (build + parity watch) must go green.

## Fixture byte-parity verification

```bash
UP=/path/to/record-spec/record-spec-lib/src/test/resources
python3 - "$UP" <<'EOF'
import os, sys, filecmp
up, ours = sys.argv[1], "tests/resources"
up_files = {os.path.relpath(os.path.join(r, f), up)
            for r, d, fs in os.walk(up) if "/META-INF" not in r
            for f in fs}
our_files = {os.path.relpath(os.path.join(r, f), ours)
             for r, d, fs in os.walk(ours) for f in fs}
missing, extra = sorted(up_files - our_files), sorted(our_files - up_files)
diffs = [f for f in sorted(up_files & our_files)
         if not filecmp.cmp(os.path.join(up, f), os.path.join(ours, f), shallow=False)]
print("missing:", missing); print("extra:", extra); print("byte-diffs:", diffs)
assert not missing and not extra and not diffs, "fixture drift detected"
EOF
```

The same check runs in CI via the parity-watch workflow.

## Scope

- Mirrored: `record-spec-lib` and `record-spec-cmd` (the CLI).
- **Not** mirrored: `record-spec-aml` (a one-off need upstream; out of
  scope for this implementation by decision).
