## Why

Go generates with OpenAPI Generator 6.5.0, which cannot model 3.1 nullable unions and drops
inherited `allOf` fields (G1: Checkout `PayToPaymentMethod`/`UPIPaymentMethod` no longer compile).
It also emits colliding unprefixed enum constants (G3: Capital `CHECKING`/`SAVINGS`; B1:
Balance Platform `ACTIVE`). Increment 2 now gives Go the source 3.1 spec; this increment qualifies
a v7 engine and the custom templates against focused fixtures before any production regeneration.
Increment 3 of 8.

## What Changes

- Pin `go/gradle.properties` to OpenAPI Generator 7.11.0 (same as the shared buildSrc baseline) and
  verify the loaded version locally and in CI.
- Port relevant upstream v7 Go template changes into the SDK's `templates/custom` without replacing
  Adyen's client architecture; update `templates/config.yaml`.
- Fix nullable type qualification so primitives and interfaces never become `common.interface{}`.
- Remove the assumption that every union member has `isValidType()`; support `allOf`, discriminated
  and non-discriminated `oneOf`, and `anyOf`.
- Prefix enum constants with their type name where unprefixed names would collide.
- Add a generation fixture suite (small specs plus the real IEX-3881 models) that is generated,
  formatted, compiled, and tested.

## Capabilities

### New Capabilities
- `go-code-generation`: what generated Go models and services must support for OpenAPI 3.1 input.

### Modified Capabilities
None.

## Impact

- Automation: `go/gradle.properties`, generation fixture specs and a fixture task/test.
- Go SDK: `templates/custom/*`, `templates/config.yaml`, shared helpers in `src/common`.
- Resolves G1, G3, and the enum part of B1.
- Gate: generated fixtures format, compile, and pass serialization/deserialization tests, including
  the real IEX-3881 models. If 7.11.0 fails, stop and resolve that blocker before rollout.
