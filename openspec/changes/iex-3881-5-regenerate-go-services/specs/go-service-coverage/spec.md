## ADDED Requirements

### Requirement: Go generates every applicable catalog service
The Go project SHALL generate all catalog services that are not restricted to other projects,
including Management and Balance Platform (31 entries), through the standard pipeline.

#### Scenario: Restored services in the matrix
- **WHEN** the CI matrix is resolved for go
- **THEN** it includes management and balanceplatform

#### Scenario: Restored services compile
- **WHEN** Management and Balance Platform are generated, formatted, and built
- **THEN** `go build ./...` and `go test ./...` pass

### Requirement: API-version constants match the catalog
Each client API-version constant SHALL equal the catalog version of the generated service.

#### Scenario: Checkout
- **WHEN** Checkout is generated from v72
- **THEN** the Checkout API-version constant is v72

### Requirement: Public changes are recorded
The breaking-change ledger SHALL record, with its cause, every change to an exported identifier,
signature, constant, or wire format caused by regeneration.

#### Scenario: Removed field
- **WHEN** regeneration removes or renames an exported field
- **THEN** the ledger lists the field, the service, and whether it comes from the spec or the generator
