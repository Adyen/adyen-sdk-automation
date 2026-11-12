## Why

Capital, Session Authentication, Foreign Exchange, Document Collector, and SoftPOS Configuration
have bot PRs (#525, #591, #603, #608, #518) that fail to build: the packages reference
`common.Config` endpoint fields that do not exist (G4), Document Collector references an undefined
`DocumentContext` and lacks `os` imports (G2), and none is reachable from `adyen.APIClient`.
Increment 7 of 8.

## What Changes

- Generate each API from the pinned current spec as a separate feature PR on the migration branch.
- Add, per API: `adyen.APIClient` accessor, `common.Config` endpoint field, TEST/LIVE routing,
  API-version constant, request/response tests, README entry, and compat routing expectations.
- Fix the Document Collector multipart generation (G2).
- Decide how standalone Capital relates to the existing `transfers.CapitalApi` (S4).
- Check already generated services (for example PosMobile) for missing client wiring.
- Verify idempotency headers where specs expose them; PF-3045 is an upstream-spec dependency.

## Capabilities

### New Capabilities
- `go-api-client-wiring`: what makes a generated Go API usable through the documented client.

### Modified Capabilities
None.

## Impact

- Go SDK `src/<api>`, `src/adyen/api.go`, `src/common/configuration.go`, README, tests.
- Automation: catalog entries already exist; no catalog change expected.
- Resolves G2, G4, and S4.
- Gate: every intended API is usable through the documented client entry point, not merely present
  as model files.
