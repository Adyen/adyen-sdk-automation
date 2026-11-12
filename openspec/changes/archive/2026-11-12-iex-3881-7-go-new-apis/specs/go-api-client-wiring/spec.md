## ADDED Requirements

### Requirement: Every generated API is reachable from the client
Each generated Go API SHALL have an `adyen.APIClient` accessor, a `common.Config` endpoint field,
TEST and LIVE base URLs matching the spec's servers, and an API-version constant.

#### Scenario: New API in TEST
- **WHEN** a client is created for the TEST environment and calls a new API
- **THEN** the request goes to the spec's TEST server URL with the configured authentication

#### Scenario: Routing fixture
- **WHEN** a new accessor is added
- **THEN** `tests/compat` contains its TEST and LIVE routing expectations

### Requirement: New APIs are documented and tested
Each new API SHALL have request/response tests and a README entry.

#### Scenario: Release review
- **WHEN** v22 is prepared for release
- **THEN** the README lists Capital, Session Authentication, Foreign Exchange, Document Collector, and SoftPOS Configuration

### Requirement: No divergent duplicate surfaces
A new package SHALL NOT ship while the same API exists inside another package (as
`transfers.CapitalApi` does) until the relationship between both surfaces is decided and documented.

#### Scenario: Capital
- **WHEN** the standalone Capital package is added
- **THEN** the migration notes state which Capital surface to use and the status of the other
