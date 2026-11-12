## Why

The Go SDK's generated code lags the specs by the unmerged bot PR backlog (#516-#609), and
Management and Balance Platform are excluded from Go in `config/services.json` (G6) because the
6.5.0 output did not compile. With the v7 engine qualified (increment 3) and the configuration
consolidated (increment 4), existing services can be regenerated and both services restored,
bringing Go to 31 catalog entries. Increment 5 of 8.

## What Changes

- Regenerate existing services in small batches: a small API first, then Checkout, Legal Entity
  Management, Transfers, Management, Balance Platform, then the rest.
- Remove `"excludedProjects": ["go"]` from Management and Balance Platform once both generate and
  pass SDK tests; update catalog and matrix test expectations in the same change.
- Update client API-version constants to the catalog versions (for example Checkout v71 → v72).
- Keep a breaking-change ledger; review public type and signature changes separately from
  mechanical generated changes.

## Capabilities

### New Capabilities
- `go-service-coverage`: which catalog services Go generates and how regenerated output is accepted.

### Modified Capabilities
None.

## Impact

- Go SDK `src/*` (generated), `src/adyen` client constants, `tests/compat` routing expectations for
  restored accessors; automation `config/services.json`, `.github/scripts` tests, buildSrc tests.
- Resolves G6 and the remaining part of B1.
- Gate: both previously disabled services generate successfully through the real pipeline; existing
  request-builder examples and HTTP contract tests pass.
