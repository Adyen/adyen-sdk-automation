# spec-staging Specification

## Purpose
Defines how each generator project obtains its own processed copy of the pristine source OpenAPI
specs, and which projects keep the source OpenAPI version.

## Requirements
### Requirement: Source specs stay pristine
The `:specs` task SHALL only clone the OpenAPI specs. No task MUST write to `schema/`.

#### Scenario: Generation leaves the clone untouched
- **WHEN** any project stages or generates any service
- **THEN** `git -C schema status --porcelain` is empty

### Requirement: Each project stages its own spec
Each applicable service SHALL have a `prepareSpec<Service>` task that writes the processed spec to
`<project>/build/specs/<spec>-v<version>.json`, and `generate<Service>` MUST use that file as its
input and depend on that task.

#### Scenario: Two projects stage the same service
- **WHEN** java and go stage the same service in one Gradle invocation
- **THEN** each reads the unmodified source and writes its own staged file

### Requirement: Go preserves the source OpenAPI version
When `sdkAutomation.preserveOpenApiVersion` is `true`, staging MUST keep the source `openapi`
version and all OpenAPI 3.1 constructs, including type arrays with `null` and `oneOf` members of
`type: null`. The Go project SHALL set it to `true`.

#### Scenario: Nullable union in a Go spec
- **WHEN** Go stages a spec with `"type": ["string", "null"]`
- **THEN** the staged spec contains `"openapi": "3.1.0"` and the same type array

### Requirement: Other projects keep their previous input
When `preserveOpenApiVersion` is `false` (the default), staging SHALL set `openapi` to `3.0.0`, and
the staged spec MUST be byte-identical to what the previous in-place pipeline produced.

#### Scenario: Parity with the previous pipeline
- **WHEN** java, php, node, python, ruby, or dotnet stage any applicable service
- **THEN** the staged file equals the previous pipeline's processed file for that project

### Requirement: Existing annotations are preserved
Staging SHALL copy `x-methodName` into `operationId` for every project, rename the `General` tag
to the service name for small services when `removeTags` is `true`, and mark webhook payload
models with `x-webhook-root` (plus one `x-has-at-least-one-webhook-root`) for webhook services only.

#### Scenario: Small service in a project with removeTags disabled
- **WHEN** go or php stage a small service
- **THEN** the `General` tag is kept

#### Scenario: Non-webhook service
- **WHEN** any project stages a service whose name does not end with `Webhooks`
- **THEN** the staged spec contains no `x-webhook-root`

