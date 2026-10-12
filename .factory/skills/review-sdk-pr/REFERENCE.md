# SDK PR Review Policy

This file defines what to judge and how to label it. The procedure, retrieval,
boundaries, and report format live in [SKILL.md](SKILL.md).

## Correctness findings

Focus exclusively on:

- **Incorrect behavior and implementation mistakes:** broken control flow,
  invalid generated references or types, inconsistent model/service changes,
  and regressions in previously supported behavior.
- **Public API and compatibility breaks:** removed or renamed symbols, changed
  signatures or types, constructor changes, and newly enforced requirements.
- **Serialization and deserialization:** incorrect wire names, required versus
  optional fields, nullability, enum values and handling, dates, schema
  composition, and discriminators that produce invalid requests or lose or
  misinterpret response data.
- **Service calls:** incorrect HTTP methods, paths, API versions, parameter
  placement or encoding, request bodies, authentication, and response handling.
- **Security and reliability:** concrete security defects or failure scenarios;
  inspect webhook payload handling and signature verification when affected.
- **Validation and error handling:** missing or incorrect checks only when they
  cause demonstrably incorrect behavior.

Report only high-confidence issues introduced by the PR. Do not flag style,
formatting, subjective improvements, speculative concerns, or pre-existing
defects. A deliberate spec-driven API change is not automatically a bug; label
it in the inventory instead. A compatibility finding must explain a concrete
consumer break, not merely note that generated text changed.

Anchor each finding to an exact changed file and line whenever possible. Cite
evidence, explain the failure scenario and user impact, and recommend an
actionable fix. Check enough surrounding code to rule out an existing mechanism
that already handles the suspected problem.

## Change inventory and grouping

Inspect every change the PR introduces, not just bugs or breaking changes:
added, removed, renamed, and changed public classes/models, enums and values,
constructors/parameters, fields/properties/accessors, serialized properties
(even with private backing fields), and service methods/parameters. Also
inspect serialization, deserialization, validation, webhook, deprecation, and
replacement behavior.

Keep symbol-level evidence (change kind, fully qualified owner and symbol,
before/after behavior, source path and changed lines) as working notes, not
report output. Consolidate it into user-facing items, classify and sort them
using the policy below, then assign stable IDs (`C1`, `C2`, ...) in displayed
order, with a representative source location or diff link.

Grouping rules:

- **One capability, one item.** A feature owns its new models and all related
  additions to existing requests, responses, and resources, across files.
  Fold constructor/accessor, serializer, validator, export, and documentation
  support into the same item. A new endpoint is one item naming its HTTP
  method/path, generated service method, and request/response support.
- **Combine similar additions.** Same-kind additions on one model, and a field
  added to both a request and its response, form one item. Name the fields and
  owners as unnumbered details, not separate IDs.
- **Keep different compatibility impacts separate.** Split an item when its
  effects differ in compatibility. Do not merge unrelated behavior merely
  because it shares a model or service.
- **Repeated cross-file edits are one item.** The same small hunk (typically
  1-4 lines, identical or differing only in names) repeated across many files
  rarely comes from per-schema spec changes. It usually comes from a template,
  the generator version or configuration, pre/postprocessing, or spec-wide
  metadata such as the `info` description or version. Report the pattern once,
  with its affected file count and one representative location, and label it
  by its effect. Attribute its likely source per the generation-evidence rules.
- **Summarize parent removal once.** Removing a model, enum, or endpoint covers
  its members. List member removals only when the parent remains.
- **State transitions explicitly.** Name the owning model/member, enum/value,
  or method and give before -> after: optional -> required, nullable ->
  non-nullable, old -> new type/name/signature, or changed wire representation.
  List added/removed enum values by owner.
- **Category headings are navigation only.** Use the ordered groups below and
  omit empty groups. Fold documentation, tests, and formatting-only edits into
  concise other-change items when not already covered; never turn them into
  findings.

Examples, when supported by the actual diff:

- `CheckoutForwardResponse.accountUpdate` and `.networkToken`, including their
  new result models, become one forwarding-results item.
- `CreateCheckoutSessionRequest.payable` and
  `CreateCheckoutSessionResponse.payable` become one session-payability item.
- `OpiRequest`, `OpiResponse`, and related `opi` additions on `PaymentRequest`,
  `StoredPaymentMethodRequest`, `PaymentResponse`, `PaymentDetailsResponse`, and
  `StoredPaymentMethodResource` become one OPI-support item.

### Reporting exclusions

Pure generation bookkeeping is not a user-facing change: `sdk-generation-log`
updates, generated timestamps, and recorded spec/automation/library commit
revisions. Read it as provenance evidence, but do not emit items, headings, or
routine verdict/release-impact commentary for it. Surface it only when material
to a finding or review limitation.

### Coverage checks

- Every changed public/serialized symbol and behavior maps to exactly one item.
  Every other change is covered by an item or by the reporting exclusions.
- No item breaks the grouping rules above (re-check for over-fragmentation).
- Every item has the matching emoji/type label and evidence, and appears once
  in its category. Check the category order and assign IDs in displayed order.
- Findings reference change IDs instead of repeating the inventory.
- If coverage is incomplete, name the gap instead of claiming a complete list.

## Change classification and ordering

Assess compatibility from the code. A confirmed break is an incompatible
change to an existing SDK contract: removed or renamed API, changed existing
method/constructor signatures, newly enforced inputs for existing calls, or
incompatible existing types, runtime behavior, or wire representation. Explain
the concrete consumer impact. Existing contracts and supported call forms
remain compatible under the additive-release policy below. If evidence cannot
establish compatibility, state what is missing rather than guessing.

Use the first applicable row for each consolidated item. Display the nonempty
groups in this exact order, with the matching emoji/type label beside every
change:

| Order | Group heading | Item label | Applies to |
|---|---|---|---|
| 1 | 💥 Breaking changes | `💥 Breaking change` | A confirmed existing-contract break, even when part of a feature or fix |
| 2 | ✨ New features | `✨ New feature` | A new user-facing capability without a confirmed break |
| 3 | 🐛 Fixes | `🐛 Fix` | A correction of existing behavior without a confirmed break or new capability |
| 4 | 🧹 Other changes | `🧹 Other change` | Remaining reportable changes, subject to the reporting exclusions |

Do not render compatibility as Yes/No/Unclear labels or repeat a change in
multiple categories. An unresolved compatibility question is not proof of a
break: use the best-supported change type and explain the uncertainty in the
item or review limitations. The release table handles its SemVer impact.

**Additive-release policy:** new enum values, discriminated-union or
payment-method alternatives, models, optional fields, and endpoints are
compatible additions when existing values, members, call forms, requirements,
and runtime/wire behavior are retained. Consumer-side exhaustiveness checks
(switches, exhaustive maps, `never` checks) don't count as breaks.

Judge the generated SDK change, not the raw spec addition: an addition can
still carry a break, such as a changed existing signature or an optional input
now enforced as required.

Examples:

- Add `PayByBankCADirectDebitDetails` to `PaymentRequestPaymentMethod` and its
  discriminator mapping, keeping existing alternatives: `✨ New feature`.
- Add `PaymentDetails.TypeEnum.Satispay`, keeping existing values and wire
  representations: `✨ New feature`.
- Add an enforced required parameter to an existing service method:
  `💥 Breaking change`.
- Correct an existing serializer's wrong wire name while preserving the
  supported SDK contract: `🐛 Fix`.
- Update documentation only: `🧹 Other change`.

## Release classification

Take the first matching row:

| Condition | Change type | SemVer impact |
|---|---|---|
| Any `💥 Breaking change` item, intentional or not | `Breaking change` | `Major` |
| Any unresolved compatibility question that could change the result | Best-supported type | `Needs maintainer decision` |
| Any `✨ New feature` item | `New feature` | `Minor` |
| Only `🐛 Fix` items, optionally with other changes | `Bug fix` | `Patch` |
| Only `🧹 Other change` items or excluded bookkeeping | `No user-facing release impact` | `None` |

Confidence:

- `High`: complete diff reviewed; every label rests on direct code evidence.
- `Medium`: complete diff reviewed; some labels rely on inference (for example
  unresolved generation inputs) that cannot change the SemVer impact.
- `Low`: coverage is incomplete, or inference could change the SemVer impact.

## Generation evidence

Use only as needed to understand a change or validate a suspected defect.

- Sources: the service's `sdk-generation-log/<service>.json` at PR head and
  comparison base (may record `openapiCommitSha`, `automationCommitSha`,
  `libraryCommitSha`), PR commits, linked spec commits, and generation-run
  evidence. Establish the previous spec revision from the base log; do not
  assume the new spec commit's parent was the previous generation input.
- A spec commit linked in the PR description may be stale or wrong. Cross-check
  candidates against the actual spec and code changes. Distinguish verified
  inputs from inferred or unresolved ones.
- Resolve template paths and generator versions/settings from
  `<language>/build.gradle.kts` in the automation repository, including task
  overrides. Templates live in the SDK repository. Account for spec
  preprocessing and code postprocessing before calling a difference from the
  raw spec a defect.
- Prefer inputs at the recorded generation revisions. Do not silently
  substitute the current local checkout, today's `main`, or the PR head's
  templates for historical inputs.
- Trace supported findings and repeated cross-file edits to the spec,
  template, automation pre/postprocessing, upstream generator, manual code, or
  an unresolved source. For repeated edits, check template, generator
  version/configuration, and spec-wide metadata changes first. Mark an
  attribution unverified when no evidence confirms it. Prefer a durable
  source-level fix over patching regenerated code.
- If an input cannot be established, disclose it as a limitation and continue.
  Missing provenance is not a defect and does not suppress supported findings.
