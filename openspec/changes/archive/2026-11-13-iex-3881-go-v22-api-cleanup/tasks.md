## 1. Layout and removals

- [x] 1.1 Move packages to the module root; rewrite imports, docs, release workflow, and the automation layout
- [x] 1.2 Remove `posterminalmanagement`, its accessor, constants, and `Config` endpoint
- [x] 1.3 Remove `CreateHTTPRequest` and `MakeHTTP*Request`

## 2. Errors

- [x] 2.1 Add `*common.APIError` for both error formats with `Unwrap` and lenient scalar decoding
- [x] 2.2 Remove `RestServiceError` and the per-status mapping from templates and automation
- [x] 2.3 Tests for classic, problem details, numeric codes, non-JSON, empty, and undecodable 2xx bodies

## 3. Enums

- [x] 3.1 Resolve inline enums to named types without schema reuse; title array item enums in staging
- [x] 3.2 Name constants from `x-enum-varnames` set to the values; drop the type prefix
- [x] 3.3 Decode unknown values; keep `IsValid` and `New<Enum>FromValue`
- [x] 3.4 Fixture tests pin names and unknown-value decoding; SpecProcessor tests for both staging options

## 4. Gate

- [x] 4.1 Regeneration is idempotent; build, vet (with and without `integration`), and test pass on Go 1.23.0 and the current toolchain
- [x] 4.2 Ledger and `apidiff` reports updated
