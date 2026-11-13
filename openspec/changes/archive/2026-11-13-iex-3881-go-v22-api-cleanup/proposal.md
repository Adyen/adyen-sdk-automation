## Why

v22 is a major version, so the Go SDK can drop surfaces that only exist for history and make its
types safer before the release: the `src/` directory in every import path, the frozen POS Terminal
Management API, raw request helpers, two unrelated error types, and enum fields typed as `string`.
Part of the v22 migration, before increment 8.

## What Changes

- **BREAKING** Packages move from `src/` to the module root (`.../v21/checkout`).
- **BREAKING** Remove `posterminalmanagement` and its client accessor, constants, and endpoint.
- **BREAKING** Remove `common.CreateHTTPRequest` and `Client.MakeHTTP*Request`; keep `WithIdempotencyKey`.
- **BREAKING** Every failed call returns `*common.APIError`, which covers classic and problem-details
  error bodies; `common.RestServiceError` and the per-status mapping in generated services go away.
- **BREAKING** Inline enums become named string types (array items too) with lenient decoding and
  `IsValid()`; top-level enum constants lose the generator prefix (`CalculationTypeLRSTCS`).

## Capabilities

### Modified Capabilities
- `go-generation-configuration`: package directories at the repository root; no error-model switch.
- `go-code-generation`: typed inline enums, Go-style constant names, lenient decoding.
- `go-api-client-wiring`: single error type; example paths.

## Impact

- Go SDK: every package path, `common` (errors, client), `adyen`, templates and `config.yaml`,
  README and docs, tests.
- Automation: `GoServiceLayout` directories, `GoServices` (no `hasRestServiceError`), spec staging
  options `nameArrayItemEnums` and `enumValuesAsVarNames`, Go inline schema options.
