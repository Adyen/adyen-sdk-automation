## Context

`adyen.NewClient` builds per-service clients from `common.Config`; endpoint fields and
`SetEnvironment` decide TEST/LIVE URLs. The routing fixture fails when an accessor lacks an
expectation, so wiring and tests land together.

## Goals / Non-Goals

**Goals:** five new APIs usable via `client.<Api>()`; consistent routing; no duplicate surfaces.

**Non-Goals:** server-side idempotency support (PF-3045); changes to existing APIs' routing.

## Decisions

- **Regenerate instead of merging stale bot output.** Reuse PR descriptions and tests where useful.
- **Wiring is hand-written but follows one pattern** (accessor, config field, environment URLs).
  Alternative considered: template-generate `api.go` wiring; deferred unless the pattern proves
  stable across all five.
- **Capital vs `transfers.CapitalApi` (S4):** keep `transfers.CapitalApi` for compatibility and add
  the standalone package; document which to use. To be confirmed with the API owners before merge.

## Risks / Trade-offs

- [Spec servers differ from the URL pattern used by `SetEnvironment`] → derive URLs from each
  spec's `servers` and assert them in routing fixtures (S3 was this class of bug).

## Open Questions

- Should `transfers.CapitalApi` be deprecated in v22?
