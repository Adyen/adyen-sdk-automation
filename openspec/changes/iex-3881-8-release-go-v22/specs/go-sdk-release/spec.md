## ADDED Requirements

### Requirement: Module path carries the major version
The Go SDK SHALL use the module path `github.com/adyen/adyen-go-api-library/v22`, and no source,
test, template, generator config, or example MUST reference the previous major.

#### Scenario: Leftover reference
- **WHEN** the version check runs after propagation
- **THEN** it finds no `/v21` import or module reference

### Requirement: Release gate
Before publishing, all 31 applicable catalog entries SHALL regenerate reproducibly, and
`go build ./...`, `go vet ./...`, and `go test ./...` MUST pass on every supported Go version.

#### Scenario: Reproducibility
- **WHEN** generation runs twice from the same pinned revisions
- **THEN** the second run produces no diff

### Requirement: Published release is installable
After explicit approval and publication, a fresh module SHALL be able to fetch v22 through the Go
proxy, and migration notes MUST list every source or wire change from the breaking-change ledger.

#### Scenario: Fresh consumer
- **WHEN** a new module runs `go get github.com/adyen/adyen-go-api-library/v22@v22.0.0`
- **THEN** it resolves and builds

### Requirement: v21 history is preserved
The release SHALL NOT rewrite published v21 tags, and v21.2.1 MUST remain retracted.

#### Scenario: v21 go.mod
- **WHEN** v22 is released
- **THEN** the v21 line still retracts v21.2.1
