## Context

Regeneration from current specs changes hundreds of files, mostly backlog drift rather than
generator changes. Reviewers need to separate the two.

## Goals / Non-Goals

**Goals:** all existing services generated from the pinned specs with the v7 pipeline;
Management and Balance Platform restored; every public change recorded.

**Non-Goals:** new APIs (increment 7); handler generation (increment 6); release (increment 8).

## Decisions

- **Batches as separate commits/PRs on `feature/go-generator-upgrade`**, each with generation,
  `make fmt`, and `go test ./...` green. Alternative rejected: one regeneration commit (unreviewable).
- **Two diffs per batch:** spec drift (6.5.0 regeneration from the same specs vs v21.2.3, from the
  increment 1 baseline) and generator drift (v7 vs 6.5.0 on the same specs).
- **Restore exclusions last**, in the same change that updates `test_services_catalog.py`,
  `test_resolve_matrix_inputs.py`, and buildSrc fixtures, so CI never schedules a failing job.
- **Breaking-change ledger** in `docs/go-v22-migration/` listing type, signature, constant, and wire
  changes with their cause.

## Risks / Trade-offs

- [Management and Balance Platform still fail with v7] → keep them excluded and stop at the gate.
- [Large diff hides an API break] → the compat fixtures and the ledger review are required per batch.
