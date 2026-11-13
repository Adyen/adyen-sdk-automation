# go-api-client-wiring Specification

## Purpose
Defines what makes a generated Go API usable through `adyen.APIClient`: accessor, endpoint
configuration, routing, documentation, and tests.
## Requirements
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

### Requirement: SDK logs can go to the application's logger
`common.Config.Logger` SHALL receive the `Debug` request and response dumps at debug level, with the
API key and `Authorization` header masked, and the error response bodies selected by
`Log3XXError`, `Log4XXError`, and `Log5XXError` at warn level (error level for 5XX). Without a
logger, dumps SHALL go to the standard `log` package and error bodies to stdout.

#### Scenario: Error response with a logger
- **WHEN** `Log4XXError` and `Logger` are set and a request returns 422
- **THEN** the logger receives a warn record with the status and the response body

#### Scenario: Error response without a logger
- **WHEN** only `Log4XXError` is set and a request returns 422
- **THEN** stdout receives the response body

### Requirement: Entry points have runnable examples
The `adyen` and `hmacvalidator` packages SHALL contain godoc examples with checked output for a
payment, error details, logging, and webhook HMAC validation.

#### Scenario: Example output
- **WHEN** `go test ./src/adyen/ ./src/hmacvalidator/` runs
- **THEN** every example's output matches its `Output:` comment

