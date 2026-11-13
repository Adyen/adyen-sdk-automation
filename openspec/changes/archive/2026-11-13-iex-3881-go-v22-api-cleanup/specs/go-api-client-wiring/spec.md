## MODIFIED Requirements

### Requirement: Entry points have runnable examples
The `adyen` and `hmacvalidator` packages SHALL contain godoc examples with checked output for a
payment, error details, logging, and webhook HMAC validation.

#### Scenario: Example output
- **WHEN** `go test ./adyen/ ./hmacvalidator/` runs
- **THEN** every example's output matches its `Output:` comment

## ADDED Requirements

### Requirement: Failed calls return one error type
Every API call that fails after Adyen responded SHALL return `*common.APIError` with the HTTP status
code, the raw body, and the fields of the classic or problem-details error body. A 2xx response that
cannot be decoded SHALL return `*common.APIError` whose `Unwrap()` is the decoding error.

#### Scenario: Problem details from a platform API
- **WHEN** Balance Platform returns 422 with a problem-details body
- **THEN** `errors.As(err, &apiErr)` succeeds and `apiErr.Detail`, `apiErr.ErrorCode`, and `apiErr.InvalidFields` are set

#### Scenario: Non-JSON error body
- **WHEN** a proxy returns 502 with an HTML body
- **THEN** the error is `*common.APIError` with `StatusCode` 502 and the body in `RawBody`
