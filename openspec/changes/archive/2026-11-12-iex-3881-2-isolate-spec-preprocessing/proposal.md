## Why

`:specs` rewrites every cloned spec to `openapi: 3.0.0` in place, and the `ungroup*` and
`addWebhookExtension*` tasks edit the same shared clone (G5). The downgrade keeps 3.1 nullable
unions (`type: [string, null]`, `oneOf` with `{type: null}`) that a 3.0 parser does not
understand, which is the root of IEX-3881. Go needs the source 3.1 document, while every other
language must keep its current input. Increment 2 of 8.

## What Changes

- `:specs` only clones; `schema/json` stays identical to the pinned adyen-openapi revision.
- New per-service task `prepareSpec<Service>` in every project writes
  `<project>/build/specs/<spec>-v<version>.json`, which becomes the generator `inputSpec`.
- `SpecProcessor` applies all preprocessing in memory, driven by `SpecProcessor.Options`:
  version downgrade, `x-methodName` → `operationId`, `General` tag rename for small services,
  and `x-webhook-root` marking for webhook specs.
- New extension property `sdkAutomation.preserveOpenApiVersion` (default `false`); Go sets it to
  `true`.
- **BREAKING (build tasks only):** the `ungroup<Service>` and `addWebhookExtension<Service>` tasks
  are removed; their behavior is part of `prepareSpec<Service>`. Nothing in the repository or CI
  invokes them by name.

## Capabilities

### New Capabilities
- `spec-staging`: how each project obtains its own processed copy of a pristine source spec.

### Modified Capabilities
None.

## Impact

- `build.gradle.kts`, `buildSrc` conventions plugin, `SpecProcessor`, `SdkAutomationExtension`,
  `go/build.gradle.kts`, buildSrc tests.
- Go's generator now reads OpenAPI 3.1.0. With 6.5.0 this matches the 3.0.0 input for the current
  29 Go specs (they contain no 3.1 null unions); real 3.1 handling is qualified in increment 3.
- Gate: nullable unions survive Go staging; source files remain unchanged; other languages retain
  their previous preprocessing output.
