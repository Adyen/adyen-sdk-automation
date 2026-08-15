---
name: generate-integration-tests-scenarios
description: >-
  Create or extend curated, language-agnostic Gherkin integration test
  scenarios from an Adyen OpenAPI operation and official or approved manually
  sourced examples. Use when the user asks to generate integration test
  scenarios for an API/service and endpoint, or provides an Adyen API Explorer
  endpoint link, plus an optional example. Generate scenario coverage only for
  documented 2xx response codes. This skill only writes scenario definitions;
  it never calls Adyen or executes tests.
argument-hint: <api> <endpoint> [example-name] | <api-explorer-url> [example-name]
user-invocable: true
metadata:
  owner: sdk-automation
---

# Generate Integration Test Scenarios

## Purpose

Create one reviewable Gherkin feature selected from an Adyen OpenAPI operation.
Resolve the displayed request examples and response-example associations from
Adyen API Explorer, replace request placeholders with declarative bindings,
and create scenario coverage only for documented 2xx response entries.
Write scenarios under
`integration-test-generator/test-scenarios/`.

## Hard output invariants

These rules take precedence over examples, existing feature contents, and
general wording elsewhere in this skill:

1. Never assert an HTTP response status in an executable scenario. Use
   `Then the operation succeeds`, followed by one or two response-body
   attribute assertions. A `@response-<key>` coverage tag is required metadata,
   not a status assertion.
2. Never choose among multiple request examples on the user's behalf. When no
   `example-name` was supplied and the endpoint exposes more than one request
   example, use `AskUser` to select exactly one before writing.
3. Never choose an unmatched response example on the user's behalf. Prefer the
   response example paired by key with the selected request example. If no
   unique pairing exists and multiple response examples remain eligible for a
   2xx response, use `AskUser` to select one before writing.

When an example-selection question has more than four candidates, paginate it:
offer three examples plus `Show more examples`, then continue with the next
page until the user selects one. Show both the API Explorer label and OpenAPI
key for every example option. A custom answer containing an exact key is also
valid.

Only create or update Gherkin feature files in this workflow.
Before writing, read
`integration-test-generator/test-scenarios/README.md` and follow its structure
and conventions.

Use `integration-test-generator/test-scenarios/checkout/payments.feature` as
the canonical style reference. New features should use its concise feature
title, one-line purpose, tag ordering, JSON doc-string indentation, observable
scenario names, narrow executable response assertions, and contract-only
response structure. Do not add explanatory steps that repeat source metadata
already present in the feature header. The response-validation rules in this
skill supersede any legacy HTTP status assertions in that reference file.

When a selected 2xx response has a matching executable request example, do not
materialize the response JSON or add a separate contract-only scenario. End the
executable scenario with a general success step and one or two narrow
assertions for documented response-body attributes:

```gherkin
Then the operation succeeds
And the response field "id" is not empty
```

Never assert the HTTP response status code in an executable scenario.

Materialize response JSON only when contract-only coverage is necessary. Do
not leave such a contract-only scenario with only an example name, such as
`And response example "generic"`, when API Explorer displays a payload for it.

## Invocation

Parse `$ARGUMENTS` as:

```text
<api> <endpoint|operation> [example-name]
<api-explorer-url> [example-name]
```

Examples:

```text
/generate-integration-tests-scenarios Checkout /payments card-securedfields
/generate-integration-tests-scenarios Checkout /sessions
/generate-integration-tests-scenarios Checkout payments card-direct
/generate-integration-tests-scenarios "https://docs.adyen.com/api-explorer/Checkout/latest/post/payments" card-securedfields
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
status and its visible example name or label. API Explorer JSON is the
authoritative payload when an example is materialized in the feature; the
processed OpenAPI JSON is used to resolve the operation, schemas, response
keys, and example names.

- Parse and pretty-print extracted payloads as JSON, preserving their data
  shape and values before applying Request Bindings.
- For an executable 2xx scenario, use the response example only to establish
  its association with the request example and documented status, and to select
  one stable response-body attribute to assert. Do not write the response JSON
  into the scenario or create contract-only coverage solely to materialize it.
- Do not synthesize a payload from an OpenAPI schema or alter a payload to make
  it fit another response status.
- If the page exposes several request examples and no `example-name` was
  supplied, use `AskUser` to select one by its visible label and OpenAPI key.
  Do not default to the first example.
- For each 2xx response, prefer the response example whose key matches the
  selected request example. If there is no unique key match and several
  response examples are eligible, use `AskUser` to select one by its visible
  label and OpenAPI key. Do not default to the first response example.
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
   - If exactly one request example exists, select it.
   - If more than one request example exists, use `AskUser` to select exactly
     one by its API Explorer label and OpenAPI key.
   - Use the selected request example's matching response example when
     available.
4. For an operation without a request body, continue without a request example
   and resolve required path or query inputs instead.
5. If the operation has a request body but no OpenAPI example, use `AskUser` to
   choose one of:
   - Provide an inline request payload.
   - Reference a fixture file.
   - Provide an approved manually sourced example, citing the implementation
     test, converter, or other local source file.
   - Stop so an OpenAPI example can be added first.

An explicitly supplied `example-name` scopes generation to that exact request
example. A user selection made through `AskUser` has the same scope. Generate
only the selected example, not every example exposed by the endpoint.

Never fabricate credentials, resource identifiers, tokens, or domain-specific
request values.

The selected request example is the baseline for executable scenarios. Do not
mutate it arbitrarily in an attempt to trigger a different response.

API Explorer examples are the default source of truth for scenario payloads.
Whenever API Explorer exposes an example for the selected request or response,
use its JSON by default. Do not substitute an OpenAPI example merely because it
has the same key or is easier to resolve.
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
OpenAPI examples, treat request-example coverage and any necessary
contract-only response-example coverage as required parts of the feature:

1. Resolve examples from the API Explorer page and all of these OpenAPI
   locations before concluding that one is missing:
   - The JSON payload displayed by API Explorer for the selected request or
     response example.
   - `content.application/json.examples`, including local `$ref` values.
   - `content.application/json.example`.
   - `example` values on the resolved response schema, following local schema
     `$ref` values.
2. For every response that requires contract-only coverage but has no resolved
   example, use `AskUser` before writing or updating the feature. Offer:
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

For operations with no request body, a request example is not required. Prefer
an executable scenario when all required operation inputs can be provided and
one documented response-body attribute can be asserted. Use the contract-only
response rules when the response cannot be covered by an executable scenario.

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

- Generate a unique runtime value for every request field that needs a unique
  reference, or whose example value is a reference placeholder (for example,
  `YOUR_ORDER_REFERENCE`, `YOUR_UNIQUE_SHOPPER_ID`, or `YOUR_*_REFERENCE`).
  Use a descriptive binding name that matches the field, such as `reference`,
  `merchantReference`, or `shopperReference`:

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

Filter the resolved operation's `responses` object to documented 2xx entries
only: explicit codes from `200` through `299` and ranges such as `2XX`.
Generate at least one scenario for each included response entry. Ignore every
non-2xx entry and `default`, regardless of whether API Explorer exposes an
example for it. Do not resolve, materialize, or create a scenario for those
examples.

Order scenarios by numeric 2xx response code, followed by 2xx ranges. Never
omit an included response entry because it lacks an example.

For each included 2xx response entry:

1. Resolve its schema and all local response-example `$ref` values.
2. Resolve media-type and schema-level examples as described in
   [Example-driven output completeness](#example-driven-output-completeness).
3. Select one response example for each 2xx response entry. When
   `example-name` was supplied, select the response example with the same key
   when available. A request example selected through `AskUser` follows the
   same matching rule. Apply these associations in order:
   - The API Explorer example with the same key as the selected request
     example.
   - An API Explorer example named `generic`.
   - The sole API Explorer example for the status.
   - If multiple API Explorer response examples remain eligible after these
     rules, use `AskUser` to select one by its visible label and OpenAPI key.
   - The corresponding OpenAPI example, only when the user approved the
     fallback described in [API Explorer examples](#api-explorer-examples).
   - If no API Explorer or approved OpenAPI example exists, accept an approved
     manual response example only after recording its cited source and
     verifying it against the response schema.
   Create an executable scenario for the selected request/response example
   pairing when it is documented to produce the response. The association
   counts as response-example coverage even though the response payload is not
   written into the executable scenario. Do not add a second contract-only
   scenario for the same pairing. Use a contract-only scenario only when the
   selected response example has no matching executable request example. Do
   not generate coverage for unselected examples under the same response
   entry.
4. Decide whether the 2xx scenario is executable:
   - A 2xx response may be executable when the selected request example is
     documented to produce that response.
   - Otherwise use contract-only coverage. Do not construct requests intended
     to produce non-2xx responses.
5. For an executable scenario:
   - Include the request example and all required bindings.
   - Invoke the API operation.
   - End the invocation with `Then the operation succeeds`.
   - Add one or two assertions for documented response-body attributes. Select
     required, stable fields from the associated response example and resolved
     response schema. Prefer a returned identifier, success enum, echoed
     request value, or non-empty collection that directly demonstrates the
     operation's result.
   - Use the public JSON property name and assert only the documented value or
     shape, for example `And the response field "id" is not empty` or
     `And the response field "status" equals "active"`.
   - If no response-body attribute can be resolved from the documented example
     and schema, do not create an executable scenario. Use
     contract-only coverage or stop for an approved response example, as
     applicable.
   - Do not materialize the response example in the scenario.
   - Do not assert the HTTP response status code.
   - Do not add response-header, schema, or more than two result assertions.
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

When the filtered 2xx response set contains only `200`, generate only
`@response-200` scenarios. Do not add scenarios for hypothetical,
undocumented, or non-2xx status codes.

For executable assertions:

- Use `Then the operation succeeds` followed by one or two response-body
  attribute assertions.
- Assert stable documented response fields that validate the operation's
  outcome, for example:

  ```gherkin
  Then the operation succeeds
  And the response field "pspReference" is not empty
  And the response field "resultCode" equals "Authorised"
  ```

- Never use the HTTP response status code as an assertion.
- Do not add more than two result assertions.

## Scenario Tags

Every scenario must include one normalized response tag:

```gherkin
@response-200
@response-2xx
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
    Then the operation succeeds
    And the response field "pspReference" is not empty
    And the response field "resultCode" equals "Authorised"

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
3. Inventory the documented 2xx response codes and request/response examples already
   represented by scenarios.
4. Append scenarios for every documented 2xx response code or example pairing not
   represented.
5. Do not duplicate an existing scenario for the same response key and exact
   request/response example pairing solely because the generator was run again.
6. If the in-scope executable scenario contains an HTTP status assertion,
   replace it with `Then the operation succeeds`. Normalize its result checks
   to one or two documented response-body attribute assertions. This is
   required cleanup and does not require confirmation.
7. If an existing response scenario conflicts with the current OpenAPI
   definition, use `AskUser` to choose whether to update it or leave it
   unchanged.
8. Preserve unrelated handwritten scenarios, comments, ordering, and
   formatting.

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
     `When the API operation is invoked` step, one general operation-success
     step, and one or two documented response-body attribute assertions, with
     no HTTP status assertion or further result assertions.
   - For contract-only scenarios, no invocation step and a response
     example/schema validation step.
4. Compare the complete set of documented 2xx response keys with the response tags
   in the feature and fail validation if any response key is missing.
5. Confirm the explicitly supplied or user-selected request example is
   covered. If no selection was needed, confirm the sole request example is
   covered. For each 2xx response entry, confirm the matching, sole, or
   user-selected response example is either associated with an executable
   scenario or materialized in a contract-only scenario. Confirm unselected
   examples under the same response entry were not generated. Confirm no
   contract-only scenario was added solely to materialize a response example
   already associated with an executable scenario. When the operation has only
   a `200` response, confirm every new scenario has `@response-200`.
6. Confirm no new scenario has a non-2xx response tag, even if API Explorer
   exposes a corresponding example.
7. Re-check that the endpoint and response keys exist in the resolved OpenAPI
   specification, and that every materialized API Explorer payload belongs to
   its selected response example and validates against that response schema.
8. Confirm every executable request-example placeholder has a binding.
9. Confirm every manual example has a cited source, contains only source-backed
   values, and matches its resolved OpenAPI schema.
10. Confirm no credentials, tokens, or environment-specific identifiers were
   written.
11. Run:

   ```bash
   git diff --check -- <feature-file>
   ```

Do not run external integration tests.

## Completion Report

Report:

- Created or updated feature path.
- Source specification and endpoint.
- Selected request and response examples.
- Every documented 2xx response key and whether its scenario is executable or
  contract-only.
- Required environment variables.
- Scenario tags.
- Whether the file was created, appended, updated, or left unchanged.
