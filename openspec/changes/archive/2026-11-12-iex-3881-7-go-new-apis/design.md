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
  the standalone package; the README and ledger name `client.Capital()` as the one to use. The
  Transfers spec already deprecates every Capital operation since v4, so the generated code marks
  them deprecated.
- **SoftPOS LIVE regions:** `SetEnvironment` uses the Europe endpoint; exported constants per
  region can be assigned to `Config.SoftPOSConfigurationEndpoint`. Alternative rejected: a region
  field in `Config` (Go has no region concept yet; Java's applies to Terminal API only).
- **PosMobile:** wired as `client.PosMobile()` (README already documented it), LIVE through the
  live URL prefix like Checkout.
- **Multipart:** the API template builds a `multipart/form-data` body through
  `common.NewMultipartBody`; `SendAPIRequest` keeps an operation's `Content-Type`. This also fixes
  the Management terminal theme asset uploads. G2's `DocumentContext` and imports were already
  fixed by generator 7.11.0.

## Risks / Trade-offs

- [Spec servers differ from the URL pattern used by `SetEnvironment`] → derive URLs from each
  spec's `servers` and assert them in routing fixtures (S3 was this class of bug).

## Open Questions

None. `transfers.CapitalApi` is deprecated by its spec.
