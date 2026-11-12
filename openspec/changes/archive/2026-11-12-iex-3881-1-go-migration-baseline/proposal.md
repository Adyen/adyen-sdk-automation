## Why

The Go SDK still generates with OpenAPI Generator 6.5.0 from specs downgraded to OpenAPI 3.0.0,
which loses nullable unions (IEX-3881) and blocks several new APIs. Before changing the generator
we need a reproducible baseline, a classified failure inventory, and a compatibility gate, so that
every later increment can prove it did not break existing SDK users. Increment 1 of 8.

## What Changes

- Pin and record the automation, spec, and SDK revisions used for the migration.
- Run the existing checks and classify every failure as baseline or migration
  (inventory E1, S1-S4, G1-G6, B1, W1 in `docs/go-v22-migration/01-baseline.md`).
- Add `tests/compat` to the Go SDK on `feature/go-generator-upgrade`: public surface, routing,
  HTTP contract, JSON contract, and webhook fixtures.
- Fix the baseline SDK defects S1 (duplicate `debug` JSON tags), S2 (Go 1.27 test brittleness),
  and S3 (`PaymentsApp` doubled `/v1`). The fixes ship with v22 only.
- Decide that migration generation stays local-only.

## Capabilities

### New Capabilities
- `go-sdk-compatibility`: the compatibility fixtures that every migration increment must pass.
- `go-migration-workflow`: how migration generation is run and isolated from production updates.

### Modified Capabilities
None.

## Impact

- Go SDK branch `feature/go-generator-upgrade` (pushed, head `e889b67a`).
- Automation: `docs/go-v22-migration/01-baseline.md` only; no generator, template, catalog, or CI change.
- Gate: reproducible baseline and a documented failure inventory before regeneration. Met.
