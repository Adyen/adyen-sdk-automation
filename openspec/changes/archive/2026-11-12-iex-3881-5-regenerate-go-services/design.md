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
- **Catalog first for the restored services.** Gradle only registers tasks for applicable
  services, so the exclusion is removed before Management and Balance Platform can be generated;
  the catalog change and its test land in the same automation commit as the regeneration result.
- **`nullable` next to `$ref` is ignored.** Management `TerminalSettings` declares its 25 sections
  as `$ref` plus `nullable: true`. Both OpenAPI 3.0 and 3.1 ignore `$ref` siblings, v21 and the
  other SDKs generate plain pointers, and the PATCH endpoints do not use explicit `null` for
  sections, so Go staging drops the keyword instead of producing `Nullable*` wrappers.
- **Generator drift check.** For every package with a 6.5.0 regeneration, `apidiff` against it
  shows no incompatible change; all incompatible changes against v21.2.3 are spec changes, the
  Checkout version bump, or the removed orphan `payments.GeneralApi`.

## Risks / Trade-offs

- [Management and Balance Platform still fail with v7] → keep them excluded and stop at the gate.
- [Large diff hides an API break] → the compat fixtures and the ledger review are required per batch.
