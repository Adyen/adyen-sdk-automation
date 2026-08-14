---
name: generate-api-gherkin
description: >-
  Create or extend a curated Gherkin feature from an Adyen OpenAPI operation
  and official or approved manually sourced examples. Use when the user
  provides an API/service and endpoint, or an Adyen API Explorer endpoint link,
  plus an optional example. Generate scenario coverage for every documented
  response code. This skill only writes scenario definitions; it never calls
  Adyen or executes tests.
argument-hint: <api> <endpoint> [example-name] | <api-explorer-url> [example-name]
user-invocable: true
version: 1.8.0
metadata:
  owner: sdk-automation
---

# Generate API Gherkin

## Purpose

Create one reviewable Gherkin feature selected from an Adyen OpenAPI operation.
Resolve the displayed request and response examples from Adyen API Explorer as
JSON doc strings, replace example placeholders with declarative bindings, and
create scenario coverage for every response entry documented by the operation.
Write scenarios under
`integration-test-generator/test-scenarios/`.

Only create or update Gherkin feature files in this workflow.
Before writing, read
`integration-test-generator/test-scenarios/README.md` and follow its structure
and conventions.

Use `integration-test-generator/test-scenarios/checkout/payments.feature` as
the canonical style reference. New features should use its concise feature
title, one-line purpose, tag ordering, JSON doc-string indentation, observable
scenario names, and contract-only response structure. Do not add explanatory
steps that repeat source metadata already present in the feature header.

For every selected API Explorer example, materialize the JSON in its scenario.
Do not leave a contract-only scenario with only an example name, such as
`And response example "generic"`, when API Explorer displays a payload for it.

## Invocation

Parse `$ARGUMENTS` as:

```text
<api> <endpoint|operation> [example-name]
<api-explorer-url> [example-name]
```

Examples:

```text
/generate-api-gherkin Checkout /payments card-securedfields
/generate-api-gherkin Checkout /sessions
/generate-api-gherkin Checkout payments card-direct
/generate-api-gherkin "https://docs.adyen.com/api-explorer/Checkout/latest/post/payments" card-securedfields
```

Inputs:

- `api`: a service name from
  `buildSrc/src/main/kotlin/adyen.sdk-automation-conventions.gradle.kts`, such
  as `Checkout`, `Management`, or `BalancePlatform`.
- `endpoint`: an exact path, `operationId`, `x-methodName`, or Adyen API Explorer
  endpoint link. A transport method is not accepted or required as a separate
  input.
- `api-explorer-url`: an endpoint-level URL under
  `https://docs.adyen.com/api-explorer/`. Infer the API and endpoint from the
  URL. An overview URL is insufficient because it does not identify an
  endpoint.
- `example-name`: optional request example key from the operation.

Use `AskUser` for missing or ambiguous inputs. Do not guess an API, operation,
or example when multiple matches exist.

When both an API and API Explorer URL are supplied, verify that they identify
the same API. Stop and report the mismatch rather than selecting either one.

## Source Resolution

1. Read the service registry in
   `buildSrc/src/main/kotlin/adyen.sdk-automation-conventions.gradle.kts`.
2. Match `api` case-insensitively against `Service.name`.
3. Resolve the current specification filename using the service's `spec` and
   `version` values. The convention is:

   ```text
   <spec-or-ServiceNameService>-v<version>.json
   ```

4. Look for the processed specification at `schema/json/<filename>`.
5. If `schema/json` does not exist, run `./gradlew specs` from the automation
   repository root. This directory is ignored by Git.
6. Fail clearly if the service or specification cannot be resolved. This skill
   does not create endpoint scenarios for webhook-only specifications without
   `paths`.

Use the JSON specification because it is the same processed input used by the
SDK generators.

## Operation Resolution

Resolve the endpoint in this order:

1. API Explorer endpoint URL.
2. Exact endpoint path, for example `/payments`.
3. Exact `x-methodName`.
4. Exact `operationId`.

For an API Explorer URL:

1. Parse both supported forms:

   ```text
   https://docs.adyen.com/api-explorer/<api>/<version>/<action>/<endpoint>
   https://docs.adyen.com/api-explorer/#/<spec>/<version>/<action>/<endpoint>
   ```

2. URL-decode the endpoint, including encoded path-parameter braces.
3. Infer the service from `<api>` or `<spec>`. Normalize an optional `Service`
   suffix before matching the service registry.
4. Treat `<version>` values such as `latest` as the service registry's current
   version. If a numeric URL version differs from the configured version, use
   `AskUser` to choose the intended specification.
5. Use `<action>` only as URL metadata for disambiguation. Do not require it in
   path-form input, include it in generated filenames, or write it into Gherkin
   steps.
6. Ignore query parameters and documentation anchors after resolving the
   endpoint.

### API Explorer examples

After resolving the endpoint, obtain its API Explorer page. When the invocation
contains an API Explorer URL, use that URL. Otherwise, construct the
endpoint-level API Explorer URL from the resolved service, version, HTTP action,
and endpoint, then fetch it. Use `FetchUrl` to read the official page.

Extract the JSON shown in the API Explorer request example and in each selected
response example. Associate each response payload with its documented response
status and its visible example name or label. The API Explorer JSON is the
authoritative payload to write into the feature; the processed OpenAPI JSON is
used to resolve the operation, schemas, response keys, and example names.

- Parse and pretty-print extracted payloads as JSON, preserving their data
  shape and values before applying Request Bindings.
- Do not synthesize a payload from an OpenAPI schema or alter a payload to make
  it fit another response status.
- If the page exposes several examples for one status, use the requested
  example name when supplied. Otherwise ask the user to select one.
- If the page omits an example that is present in the OpenAPI specification,
  ask the user whether to use the specification payload, provide an approved
  manual example, or keep that response schema-only. Do not silently invent
  API Explorer JSON.
- If `FetchUrl` cannot retrieve a page whose examples are rendered dynamically,
  report that limitation and use the OpenAPI example only after the user
  confirms it. Do not scrape unrelated documentation pages.

Record:

- Endpoint path.
- `operationId` and `x-methodName`.
- Tags.
- Request body schema.
- Path, query, and header parameters.
- Request examples and their API Explorer JSON.
- Response statuses, schemas, examples, and their API Explorer JSON.

If a path maps to more than one operation and the input does not disambiguate
it, use `AskUser` to select an operation by summary or `x-methodName`.

## Example Selection

1. If `example-name` was provided, require an exact key under:

   ```text
   requestBody.content.application/json.examples
   ```

2. Resolve local `$ref` values under `#/components/examples/`.
3. When no example was provided:
   - Select it automatically only when exactly one request example exists.
   - When several exist, use `AskUser` with up to four representative example
     keys. The user can enter another key as a custom answer.
4. For an operation without a request body, continue without a request example
   and resolve required path or query inputs instead.
5. If the operation has a request body but no OpenAPI example, use `AskUser` to
   choose one of:
   - Provide an inline request payload.
   - Reference a fixture file.
   - Provide an approved manually sourced example, citing the implementation
     test, converter, or other local source file.
   - Stop so an OpenAPI example can be added first.

Never fabricate credentials, resource identifiers, tokens, or domain-specific
request values.

The selected request example is the baseline for executable scenarios. Do not
mutate it arbitrarily in an attempt to trigger every documented response.

API Explorer examples are the preferred source of truth for scenario payloads.
Preserve their business shape and replace only documented placeholders using
Request Bindings. When API Explorer supplies no suitable example, an approved
OpenAPI or manual example may be used only as described in
[API Explorer examples](#api-explorer-examples).

Manual examples must:

- Be named by the user or derived as a clear lowercase-kebab-case name from the
  cited source.
- Contain only values present in the cited source. Do not fill omitted fields
  from inference or another endpoint's example.
- Be checked against the resolved OpenAPI request or response schema.
- Replace credentials, tokens, resource IDs, and environment-specific values
  with declarative bindings or safe placeholders.
- Be identified with `@example-manual-<name>`, rather than an invented OpenAPI
  example tag.

Manual response examples support contract-only schema coverage. They do not
prove that a request produces the documented status and do not make a non-2xx
scenario executable.

### Example-driven output completeness

When the user asks for examples, or when the operation has any API Explorer or
OpenAPI examples, treat example coverage as a required part of the feature:

1. Resolve examples from the API Explorer page and all of these OpenAPI
   locations before concluding that one is missing:
   - The JSON payload displayed by API Explorer for the selected request or
     response example.
   - `content.application/json.examples`, including local `$ref` values.
   - `content.application/json.example`.
   - `example` values on the resolved response schema, following local schema
     `$ref` values.
2. For every response without a resolved example, use `AskUser` before writing
   or updating the feature. Offer:
   - Stop so an OpenAPI example can be added, then rerun the skill.
   - Continue with schema-only contract coverage for the missing responses.
   - Provide an approved manual response example, citing an implementation
     test, converter, fixture, or inline payload.
3. For a manually sourced response example, record its name and source in a
   comment immediately above the scenario, materialize it as a JSON doc string,
   use `@example-manual-<name>`, and assert it with:

   ```gherkin
   And the manual response example "<name>" is:
     """json
     {
       "field": "source-backed value"
     }
     """
   Then the manual response example matches the documented response schema
   ```

4. Do not manufacture a `generic` example, reuse an example from another
   endpoint or service, or add `@example-<name>` without a resolved API
   Explorer or OpenAPI example.

For operations with no request body, a request example is not required. The
rule still applies independently to every documented response.

## Request Bindings

Inspect every selected request value and emit declarative bindings instead of
copying environment-specific values into the feature.

Use these transformations:

- Materialize the resolved request example as a JSON doc string.
- `YOUR_MERCHANT_ACCOUNT` becomes a named runtime value:

  ```gherkin
  And the shared merchant account is available as "merchantAccount"
  ```

  Use `"merchantAccount": "${merchantAccount}"` in the request JSON.

- Order and merchant references that must be unique become:

  ```gherkin
  Given a unique value is available as "reference"
  ```

  Use `"reference": "${reference}"` in the request JSON.

- Example return URLs become the safe literal:

  ```json
  "returnUrl": "https://example.com/checkout/return"
  ```

- If the operation accepts `Idempotency-Key`, add:

  ```gherkin
  And a unique idempotency key is available as "idempotencyKey"
  ```

- Other `YOUR_*` placeholders require an explicit environment variable,
  generated value, fixture, or literal supplied by the user.

Use `${name}` interpolation for runtime values inside request JSON doc strings.
Use the public JSON property names from the OpenAPI schema for response
assertions. Account for every obvious placeholder in the selected request. Do
not write the feature while an unresolved placeholder remains.

For required path and query parameters, use:

```gherkin
And path parameter "merchantId" comes from environment "ADYEN_MERCHANT_ID"
And query parameter "pageSize" equals 10
```

Ask the user for mappings that cannot be derived safely.

## Response Scenario Generation

Enumerate every key under the resolved operation's `responses` object. Generate
at least one scenario for each documented response entry, including explicit
codes, ranges such as `2XX`, and `default`.

Order scenarios by numeric response code, followed by ranges and `default`.
Never omit a response entry because it lacks an example.

For each response entry:

1. Resolve its schema and all local response-example `$ref` values.
2. Resolve media-type and schema-level examples as described in
   [Example-driven output completeness](#example-driven-output-completeness).
3. Select a representative response example in this order:
   - The API Explorer example with the same key as the selected request
     example.
   - An API Explorer example named `generic`.
   - The sole API Explorer example for the status.
   - The corresponding OpenAPI example, only when the user approved the
     fallback described in [API Explorer examples](#api-explorer-examples).
   - If several examples remain, use `AskUser` to select one or choose
     status/schema-only coverage. Batch ambiguous statuses into questionnaires
     of no more than four questions.
   - If no API Explorer or approved OpenAPI example exists, accept an approved
     manual response example only after recording its cited source and
     verifying it against the response schema.
4. Decide whether the scenario is executable:
   - A 2xx response may be executable when the selected request example is
     documented to produce that response.
   - A non-2xx response is executable only when OpenAPI provides a matching
     request example or fixture that explicitly triggers it.
   - Authentication, authorization, rate-limit, server-error, and generic error
     responses are contract-only unless the user explicitly supplies a safe,
     deterministic trigger.
   - Do not send intentionally invalid credentials, remove permissions, cause
     rate limits, or attempt to trigger server errors.
5. For an executable scenario:
   - Include the request example and all required bindings.
   - Invoke the API operation.
   - Assert the documented response status.
   - Add only narrow, stable body assertions.
6. For a contract-only scenario:
   - Do not invoke the API.
   - Reference the documented response status or response key. The feature
     header already records the OpenAPI endpoint, so do not add a redundant
     `Given OpenAPI endpoint` step.
   - Materialize the selected API Explorer, approved OpenAPI, or manual
     response example as a JSON doc string when one exists.
   - Assert that the selected example matches the documented response schema.
   - When no example exists, assert that the response definition and schema are
     present and valid.

For executable assertions:

- Assert stable enum or status fields.
- Assert stable booleans or types.
- Assert required identifiers as non-empty strings.
- Compare echoed values with request fields.
- Do not assert exact PSP references, generated IDs, timestamps,
  authentication codes, URLs, tokens, hashes, or complete response objects.
- Do not use a generic error response as evidence for a specific negative
  behavior. Exact error codes or messages require a matching documented example
  or explicit user input.

Supported assertion steps include:

```gherkin
Then the call succeeds with status 200
Then the call fails with status 422
Then the response status is 302
And response field "/resultCode" equals "Authorised"
And response field "/pspReference" is a non-empty string
And response field "/merchantReference" equals request field "/reference"
And error field "/errorCode" equals "138"
Given documented response status 401
Given documented response key "default"
And the API Explorer response example "generic" is:
  """json
  {
    "status": 401,
    "errorCode": "000",
    "message": "HTTP Status Response - Unauthorized",
    "errorType": "security"
  }
  """
Then the response example matches the documented response schema
And the manual response example "source-name" is:
  """json
  {
    "field": "source-backed value"
  }
  """
Then the manual response example matches the documented response schema
Then the response definition and schema are present and valid
```

## Scenario Tags

Every scenario must include one normalized response tag:

```gherkin
@response-200
@response-2xx
@response-default
```

Executable scenarios must include:

```gherkin
@external @test-only
```

Contract-only scenarios must include:

```gherkin
@contract-only
```

Also add:

- `@side-effect` to executable scenarios for operations that create, update,
  submit, transfer, pay, refund, cancel, or delete remote state.
- `@manual` when an executable scenario requires a terminal, person, dedicated
  infrastructure, pre-existing resource, or cleanup that cannot be expressed.
- `@read-only` to executable scenarios for operations that only retrieve or
  list data.
- `@example-<name>` when the scenario uses a resolved OpenAPI request or
  response example.
- `@example-manual-<name>` when the scenario uses an approved manually sourced
  example.

This skill creates files only. Never execute the scenario or make an external
API request.

## Output Format

Group scenarios by API and OpenAPI service tag, with one feature file per
service:

```text
integration-test-generator/test-scenarios/<api-id>/<service-id>.feature
```

Examples:

```text
integration-test-generator/test-scenarios/checkout/payments.feature
integration-test-generator/test-scenarios/checkout/modifications.feature
```

Build `<api-id>` and `<service-id>` as lowercase kebab-case values. Derive the
service from the operation's OpenAPI tag. If an operation has multiple service
tags that map to different files, use `AskUser` to select the target service.

Use this shape:

```gherkin
# Source: CheckoutService-v72.json
# Endpoint: /payments

@integration @checkout @payments
Feature: Checkout payments
  Payment scenarios shared by all generated SDK integration test suites.

  Background:
    Given the Checkout API is configured for the TEST environment
    And the shared merchant account is available as "merchantAccount"

  @external @test-only @side-effect @response-200 @example-card-securedfields
  Scenario: Make a successful card payment
    Given a unique value is available as "reference"
    And the payment request is:
      """json
      {
        "amount": {
          "currency": "USD",
          "value": 1000
        },
        "reference": "${reference}",
        "paymentMethod": {
          "type": "scheme",
          "encryptedCardNumber": "test_4111111111111111",
          "encryptedExpiryMonth": "test_03",
          "encryptedExpiryYear": "test_2030",
          "encryptedSecurityCode": "test_737"
        },
        "returnUrl": "https://example.com/checkout/return",
        "merchantAccount": "${merchantAccount}"
      }
      """
    When the "payments" operation is called
    Then the operation succeeds with HTTP status 200
    And the response field "pspReference" is not empty
    And the response field "resultCode" equals "Authorised"

  @contract-only @response-400 @example-generic
  Scenario: Validate the documented 400 response
    Given documented response status 400
    And the API Explorer response example "generic" is:
      """json
      {
        "status": 400,
        "errorCode": "702",
        "message": "Unexpected input: \", expected: }",
        "errorType": "validation"
      }
      """
    Then the response example matches the documented response schema

  @contract-only @response-401 @example-generic
  Scenario: Validate the documented 401 response
    Given documented response status 401
    And the API Explorer response example "generic" is:
      """json
      {
        "status": 401,
        "errorCode": "000",
        "message": "HTTP Status Response - Unauthorized",
        "errorType": "security"
      }
      """
    Then the response example matches the documented response schema

  @contract-only @response-403 @example-generic
  Scenario: Validate the documented 403 response
    Given documented response status 403
    And the API Explorer response example "generic" is:
      """json
      {
        "status": 403,
        "errorCode": "901",
        "message": "Invalid Merchant Account",
        "errorType": "security",
        "pspReference": "881611827877203B"
      }
      """
    Then the response example matches the documented response schema

  @contract-only @response-422 @example-generic
  Scenario: Validate the documented 422 response
    Given documented response status 422
    And the API Explorer response example "generic" is:
      """json
      {
        "status": 422,
        "errorCode": "14_030",
        "message": "Return URL is missing.",
        "errorType": "validation",
        "pspReference": "8816118280275544"
      }
      """
    Then the response example matches the documented response schema

  @contract-only @response-500 @example-generic
  Scenario: Validate the documented 500 response
    Given documented response status 500
    And the API Explorer response example "generic" is:
      """json
      {
        "status": 500,
        "errorCode": "905",
        "message": "Payment details are not supported",
        "errorType": "configuration",
        "pspReference": "8516091485743033"
      }
      """
    Then the response example matches the documented response schema
```

Use `Feature: <API> <service>` and `<Service> scenarios shared by all generated
SDK integration test suites.` when it accurately describes the service, matching
the Checkout feature. Otherwise, use the same concise style with a
service-specific purpose. Derive executable scenario names from the selected
example's summary, rewriting them as observable behavior when necessary. Name
contract-only scenarios after their documented response code or key.

## Existing Files

If the target file exists:

1. Read it before editing.
2. Confirm its API and service tags match the target API and OpenAPI service.
3. Inventory the response codes already represented by scenarios.
4. Append scenarios for every documented response code not represented.
5. If a response code is already represented, do not duplicate it solely
   because the generator was run again.
6. If an existing response scenario conflicts with the current OpenAPI
   definition, use `AskUser` to choose whether to update it or leave it
   unchanged.
7. Preserve handwritten scenarios, comments, ordering, and formatting.

Never overwrite an existing feature wholesale.

## Validation

Before finishing:

1. Re-read the generated or updated file.
2. Confirm it has one `Feature:` declaration.
3. Confirm every new scenario has:
   - A normalized `@response-<key>` tag.
   - Exactly one of `@external` or `@contract-only`.
   - A resolved OpenAPI endpoint recorded in the feature header.
   - For executable scenarios, a request example, fixture, inline payload, or
     no-body operation.
   - For executable scenarios, exactly one
     `When the API operation is invoked` step and a status assertion.
   - For contract-only scenarios, no invocation step and a response
     example/schema validation step.
4. Compare the complete set of documented response keys with the response tags
   in the feature and fail validation if any response key is missing.
5. Re-check that the endpoint and response keys exist in the resolved OpenAPI
   specification, and that every materialized API Explorer payload belongs to
   its selected response example and validates against that response schema.
6. Confirm every executable request-example placeholder has a binding.
7. Confirm every manual example has a cited source, contains only source-backed
   values, and matches its resolved OpenAPI schema.
8. Confirm no credentials, tokens, or environment-specific identifiers were
   written.
9. Run:

   ```bash
   git diff --check -- <feature-file>
   ```

Do not run external integration tests.

## Completion Report

Report:

- Created or updated feature path.
- Source specification and endpoint.
- Selected request and response examples.
- Every documented response key and whether its scenario is executable or
  contract-only.
- Required environment variables.
- Scenario tags.
- Whether the file was created, appended, updated, or left unchanged.
