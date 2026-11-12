## 1. Module version

- [ ] 1.1 Add a version-propagation script and a check for leftover `/v21` references
- [ ] 1.2 Move module, imports, templates, generator config, examples, and metadata to `/v22`
- [ ] 1.3 Update `tests/compat` import paths only

## 2. Validation

- [ ] 2.1 Generate all 31 catalog entries, `make fmt`, and regenerate; no diff
- [ ] 2.2 `go build`, `go vet`, `go test ./...` on Go 1.23 through the latest release
- [ ] 2.3 Credentialed integration tests against authorized test accounts

## 3. Release

- [ ] 3.1 Publish migration notes from the breaking-change ledger
- [ ] 3.2 After explicit approval, tag and publish v22.0.0
- [ ] 3.3 Verify a fresh consumer can fetch the module via the Go proxy and docs appear on pkg.go.dev
