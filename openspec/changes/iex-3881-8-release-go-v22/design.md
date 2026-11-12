## Context

Every Go import path includes the major version from v2 onward. Templates and generator config
embed the module path, so a missed location produces mixed v21/v22 imports.

## Goals / Non-Goals

**Goals:** a single command that moves all module references to the new major; reproducible
generation; a verified published release.

**Non-Goals:** redesigning module naming; publishing without explicit approval.

## Decisions

- **Scripted propagation** (one script, checked in, with a test that fails on any remaining
  `/v21` reference). Alternative rejected: manual search and replace.
- **Reproducibility check:** regenerate twice from the same pinned revisions; require no diff.
- **Release only after approval**, then verify with a fresh module (`go get .../v22@v22.0.0`) and
  pkg.go.dev availability.

## Risks / Trade-offs

- [Integration tests need credentials] → run them as a manual release gate with authorized test
  accounts; record the run in the release notes.
- [Consumers on v21 keep the retracted v21.2.1 risk] → retraction stays in v21 `go.mod`.
