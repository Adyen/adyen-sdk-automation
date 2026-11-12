# go-sdk-compatibility Specification

## Purpose
Defines the `tests/compat` suite in the Go SDK that freezes the public surface and wire behavior
every IEX-3881 migration increment must preserve.

## Requirements
### Requirement: Compatibility fixtures gate every increment
The Go SDK migration branch SHALL contain the `tests/compat` fixture suite, and every migration
increment MUST pass it with `go test ./tests/compat/` on every supported Go version.

#### Scenario: Increment changes generated code
- **WHEN** an increment regenerates or edits SDK code
- **THEN** `go test ./tests/compat/` passes without editing any fixture expectation

#### Scenario: Expectation must change
- **WHEN** an unavoidable source or wire change makes a fixture fail
- **THEN** the change is recorded in the breaking-change ledger before the expectation is updated

### Requirement: Fixtures cover the public contract
The fixtures SHALL cover client accessors and their routing, request builders, request and response
JSON (including nullable states), error types, HMAC validation, and every typed webhook handler.

#### Scenario: Retracted change is caught
- **WHEN** the fixtures run against v21.2.1, which changed `NotificationRequestItem.AdditionalData`
- **THEN** compilation fails

#### Scenario: New accessor without routing
- **WHEN** a client accessor is added without a routing expectation
- **THEN** the routing fixture fails

