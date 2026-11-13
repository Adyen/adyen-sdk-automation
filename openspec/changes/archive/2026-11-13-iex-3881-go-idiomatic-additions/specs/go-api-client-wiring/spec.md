## ADDED Requirements

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
