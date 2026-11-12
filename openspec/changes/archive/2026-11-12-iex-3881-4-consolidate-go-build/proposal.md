## Why

`go/build.gradle.kts` customizes services through scattered `tasks.named(...)` blocks: per-service
`serviceName`/`packageName` overrides, a Transfers-only `hasRestServiceError` switch (Management and
Balance Platform will need it too), and stale assertions (the `acswebhooks` check inspects
`checkout/api_default.go`). Restoring two services and adding five more (increments 5 and 7) on top
of this invites configuration leaking between services. Increment 4 of 8.

## What Changes

- One per-service configuration path in `go/build.gradle.kts` that derives package name, target
  directory, service name, small/webhook deployment rules, and error-model support for each service.
- A small explicit legacy mapping: `Payment → payments`, `LegalEntityManagement → legalentity`
  (service name `LegalEntity`), `Payout` (empty service name), singular webhook packages.
- Derive `hasRestServiceError` from the spec's error responses instead of a Transfers-only switch.
- Replace the inline `doLast` asserts with buildSrc tests.

## Capabilities

### New Capabilities
- `go-generation-configuration`: how each Go service maps to package, directory, and generator options.

### Modified Capabilities
None.

## Impact

- `go/build.gradle.kts`, possibly a helper in buildSrc, buildSrc tests.
- No generated output change for the 29 current services, except that deployment now cleans the
  real Payment and LegalEntityManagement directories, removing two stale files
  (`payments/api_general.go`, `legalentity/api/openapi.yaml`).
- Gate: historical package paths and client naming remain stable; representative services
  regenerate consistently.
