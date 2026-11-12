# go-migration-workflow Specification

## Purpose
Defines how IEX-3881 migration generation is run so that it never touches production SDK update PRs.

## Requirements
### Requirement: Migration generation is local-only
Migration generation SHALL run on a developer machine against the Go SDK branch
`feature/go-generator-upgrade`. The "Update SDKs" workflow MUST NOT be dispatched from a
migration branch of the automation repository.

#### Scenario: Developer generates migration output
- **WHEN** a developer needs generated Go code for an increment
- **THEN** they run Gradle locally with `go/repo` pointing at a checkout of `feature/go-generator-upgrade`

#### Scenario: Production bot PRs stay untouched
- **WHEN** migration work is in progress
- **THEN** no `sdk-automation/<service>` branch of the Go SDK is updated from migration code

### Requirement: Baseline revisions are recorded
Each increment SHALL state the automation, spec, and SDK revisions it was validated against.

#### Scenario: Increment report
- **WHEN** an increment's gate is reported
- **THEN** the report names the three revisions used

