## Why

Increments 2-7 change public Go identifiers and wire details that cannot ship in v21. Go requires a
`/v22` module path for a new major, and the release must prove that generation is reproducible and
that consumers can install it. Increment 8 of 8.

## What Changes

- Automate major-version propagation across `go.mod`, source and test imports, templates,
  generator configuration, examples, and version metadata; keep the Go-required `/v22` suffix.
- Generate all 31 applicable catalog entries, then regenerate to confirm reproducibility.
- Add `go vet ./...` to the SDK gate (possible since S1 is fixed) alongside build, `make fmt`
  check, tests, and the supported Go-version matrix (keep Go 1.23 unless a requirement raises it).
- Run credentialed integration tests against authorized test accounts.
- Publish migration notes listing every source or wire change from the breaking-change ledger.
- After explicit release approval, publish and verify installation through the Go proxy.
- Keep v21.2.1 retracted on the v21 line; do not rewrite published tags.

## Capabilities

### New Capabilities
- `go-sdk-release`: what must hold before and after publishing v22.

### Modified Capabilities
None.

## Impact

- Go SDK module path, imports, CI workflows, release tooling, docs; automation Go templates config.
- Gate: AC1-AC4 of IEX-3881 are satisfied by reproducible generation, passing checks, and an
  installable published release.
