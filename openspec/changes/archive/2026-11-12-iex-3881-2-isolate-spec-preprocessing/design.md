## Context

Before this change, preprocessing had three writers on `schema/json`: the `:specs` doLast
(downgrade + `x-methodName`), `ungroup<Svc>` (skipped for go and php via `removeTags=false`), and
`addWebhookExtension<Svc>`. The result depended on which projects ran in the same invocation,
and no project could see the source document.

## Goals / Non-Goals

**Goals:** pristine source specs; one processed input per project and service; Go keeps 3.1;
byte-identical staged inputs for java, php, node, python, ruby, and dotnet.

**Non-Goals:** converting 3.1 constructs for 3.0 consumers; removing the downgrade for other
languages (IEX-4094); changing generator versions or templates.

## Decisions

- **Stage under the project build dir** (`build/specs/`), so `cleanRepo` removes it and two
  projects can never share a processed file.
  Alternative rejected: one staged copy per language under `schema/` (keeps a shared mutable tree).
- **One task per service (`prepareSpec<Service>`)** combining all transformations, with the
  source file and the resolved options as task inputs and the staged file as output, so Gradle
  re-stages when the spec or the options change.
  Alternative rejected: keep separate ungroup/webhook tasks on the staged copy (ordering between
  writers of the same file is implicit).
- **Options resolved lazily** (`preserveOpenApiVersion.zip(removeTags)`), because language build
  scripts set extension values after the conventions plugin is applied.
- **`preserveOpenApiVersion` extension flag** instead of a hard-coded `project.name == "go"`
  check, so IEX-4094 can enable other languages one at a time.
- **`x-methodName` handling stays on for Go.** It only sets `operationId`, which is valid in 3.1.
- **`pmTable` reads the pristine Checkout spec.** It only reads `PaymentRequest.paymentMethod.oneOf`
  and each variant's `type` enum, which the old preprocessing never changed.

## Risks / Trade-offs

- [Serialization drift between old and new output] → staged output is the same
  `JsonOutput.prettyPrint(JsonOutput.toJson(...))` round trip; verified byte-identical against the
  old pipeline for all 188 non-Go staged specs.
- [Generator 6.5.0 reading 3.1.0 for Go] → the 29 current Go specs differ from their old input only
  in the `openapi` field; the full 3.1 path is qualified in increment 3 before regeneration.
- [External scripts calling `ungroup*`/`addWebhookExtension*`] → none found in the repository or
  workflows; noted as a build-task break in the proposal.
