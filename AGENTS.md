## Agent skills

### Issue tracker

Issues are tracked as local markdown files under `.scratch/<feature-slug>/`. See `docs/agents/issue-tracker.md`.

### Triage labels

The five canonical triage roles are used as-is (label string = role name). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `GLOSSARY.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.

### Parity process

This implementation mirrors the Kotlin `record-spec` upstream (mirror-first policy, ADR-0001). Before changing behaviour or syncing an upstream change, follow `docs/agents/parity.md`.