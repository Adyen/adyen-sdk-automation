# Go v22 migration: increment 1 baseline

Status: baseline recorded on 2026-11-12. No generator, template, catalog, or CI change has been made.
The gate for increment 1 ("reproducible baseline and a documented failure inventory before
regeneration") is met, pending review of the open decisions at the end of this document.

## Pinned revisions

| Input | Repository | Revision |
|-------|------------|----------|
| Automation | `Adyen/adyen-sdk-automation` | `ae7e576` (main, PR #171 merge) |
| OpenAPI specs | `Adyen/adyen-openapi` | `d449f090` (main, "spec release") |
| Go SDK | `Adyen/adyen-go-api-library` | `f96755ef` (tag `v21.2.3`, main) |
| Go generator | `go/gradle.properties` | OpenAPI Generator `6.5.0` (verified from `.openapi-generator/VERSION` of all 29 outputs) |
| Shared generator | `buildSrc/gradle.properties` | OpenAPI Generator `7.11.0` |

The engine is resolved from the `buildSrc` classpath. CI copies `<project>/gradle.properties`
into `buildSrc` before generating. Locally, `-DopenapiGeneratorVersion=6.5.0` has the same
effect without modifying the working tree. Running `./gradlew :go:...` without either
generates with 7.11.0 while the Go project still declares 6.5.0.

The developer checkout at `adyen-sdk-automation/go/repo` is **not** a valid baseline: it is
at `a2f06b12` (`v21.2.0-5`, 40 commits behind v21.2.3) and holds untracked Balance Platform
files. It was left untouched.

## Working copies

All under `~/workspace/api-excellence/go-v22-migration/`. Each repository has a local
`go-v22-migration` branch. Nothing has been pushed.

| Path | Purpose |
|------|---------|
| `automation/` | Automation clone; `go/repo` is a symlink to `gen-baseline-go/`, `schema/` is the spec clone created by `:specs` |
| `adyen-go-api-library/` | SDK clone at v21.2.3; carries the compatibility fixtures |
| `adyen-openapi/` | Pristine spec clone at `d449f090` |
| `gen-baseline-go/` | Worktree (branch `gen-baseline-v650`) holding the uncommitted 6.5.0 regeneration output |
| `pr525/` | PR #525 (Capital) checkout used to reproduce its CI failure |
| `baseline-logs/` | Raw logs for every command below |

## Commands and results

| Check | Command | Result |
|-------|---------|--------|
| buildSrc unit tests | `./gradlew :buildSrc:test` | Pass |
| CI script tests (Python 3.12) | `python3.12 -m unittest discover -s .github/scripts` | Pass (43 tests) |
| CI script tests (default `python3`) | `python3 -m unittest discover -s .github/scripts` | **6 errors**, environment only (see E1) |
| SDK build | `go build ./...` | Pass |
| SDK vet | `go vet ./...` | **Fails** (see S1); not run by SDK CI |
| SDK tests, Go 1.23 / 1.24 / 1.25 / 1.26 | `GOTOOLCHAIN=goX go test ./...` | Pass |
| SDK tests, Go 1.27.3 | `go test ./...` | **1 failure** (see S2) |
| Compatibility fixtures, Go 1.23-1.27 | `go test ./tests/compat/` | Pass (55 passing test cases, 1 known-defect skip) |
| Regenerate all Go services with 6.5.0 | `./gradlew -DopenapiGeneratorVersion=6.5.0 :go:services` | Generation succeeds for 29 services |
| Regenerated SDK after `make fmt` | `go build ./... && go test ./...` (Go 1.23) | **Build fails** (see G1-G4) |
| PR #525 (Capital), Go 1.23 | `go test ./...` | **Build fails** (reproduces CI, see G3/G4) |

## Failure inventory

Each failure is classified as **baseline** (exists in v21.2.3 or its environment, independent
of the migration) or **migration** (must be resolved by a planned increment).

### Environment

- **E1 (baseline, environment).** The default `python3` on this machine is 3.7.9. CI scripts
  use `dict[str, str]` annotations (3.9+). All 43 tests pass with 3.12. No action beyond
  documenting the minimum Python version.

### SDK v21.2.3 defects

- **S1 (baseline).** `go vet` fails: `Log3XXError`, `Log4XXError`, `Log5XXError` in
  `src/common/configuration.go` all reuse the JSON tag `debug` already used by `Debug`.
  `encoding/json` drops all four conflicting fields when marshalling `common.Config`. SDK CI runs only `make build` and `make test`, so this is
  invisible. Adding `go vet` to the gate (increment 8) requires fixing it, which renames the
  JSON keys: record in the breaking-change ledger.
- **S2 (baseline, Go 1.27+).** `tests/checkout/unit_test.go:95` asserts the substring
  `error calling MarshalJSON for type checkout.CheckoutPaymentMethod`; Go 1.27's
  `encoding/json` reports `*checkout.CheckoutPaymentMethod`. Test brittleness, not an SDK
  defect, but it will fail once CI adds Go 1.27 (open Renovate PR #598).
- **S3 (baseline).** `PaymentsApp()` resolves to `https://management-{test,live}.adyen.com/v1/v1`.
  The spec server is `.../v1`; `SetEnvironment` appends `/v1` and the accessor appends it
  again. No existing test covers it. The routing fixture expects the spec-correct URL and is
  skipped as a known defect until fixed.
- **S4 (baseline, note).** `transfers` already exposes `CapitalApi`. The standalone Capital
  package (increment 7) must not create two divergent Capital surfaces without a decision.

### Generation with the current pipeline (6.5.0, unchanged templates)

Regeneration from `d449f090` changes 291 tracked files (+12,585/-2,556) and adds 142 files
after `make fmt`, mostly Checkout (222 modified, 78 added), Legal Entity, Configuration
webhooks, and Transfers. This drift is the backlog of unmerged bot PRs (#516-#609), not
non-determinism. The raw generator output also has "imported and not used" errors that only
`make fmt` (goimports v0.41.0) removes, so formatting is part of the generation contract.

- **G1 (migration, increment 3).** Checkout no longer compiles: `PayToPaymentMethod` and
  `UPIPaymentMethod` are now `allOf: [ShopperIdPaymentMethod, {...}]` with an inherited
  required `type`. Generator 6.5.0 drops the inherited field but the constructor still assigns
  `this.Type`. Because `adyen` imports `checkout`, every test package fails to build. Same root
  cause as the failing bot PR #522.
- **G2 (migration, increment 7).** Document Collector references an undefined `DocumentContext`
  type and needs `os` imports for the multipart upload.
- **G3 (migration, increment 3).** Capital emits unprefixed enum constants `CHECKING` and
  `SAVINGS` from both `CALocalBankAccountType` and `USLocalBankAccountType` in one package.
  Reproduced on PR #525 with Go 1.23 (this is its CI compiler failure).
- **G4 (migration, increment 7).** New packages reference `common.Config` fields that do not
  exist: `CapitalEndpoint`, `DocumentCollectorEndpoint`, `ForeignExchangeEndpoint`,
  `SessionAuthenticationEndpoint`, `SoftPOSConfigurationEndpoint`. None are wired into
  `adyen.APIClient`. Matches failing bot PRs #525, #591, #603, #608, #518.
- **G5 (migration, increment 2).** `:specs` rewrites every cloned spec to `openapi: 3.0.0`
  in place (`schema/json/CheckoutService-v72.json` reads `3.0.0`), and the `ungroup*` and
  `addWebhookExtension*` tasks also edit the shared clone. Pristine sources are only available
  from a separate spec clone.
- **G6 (migration, increment 5).** Management and Balance Platform are excluded from Go in
  `config/services.json`, so this baseline does not regenerate them (29 applicable entries;
  31 after restoring both). Their stale bot PRs #516 and #523 remain open; #523 fails Go 1.23.

### Wire defaults worth tracking

- **W1.** `checkout.NewPaymentRequest` applies the spec default and sends
  `"threeDSAuthenticationOnly": false`. The request fixture freezes this. Default handling
  differs between generator versions, so a change here is a wire change.

## Compatibility fixtures

Added to the SDK migration branch as `tests/compat` (test-only, no production code changes):

- `surface_test.go`: compile-time guards for `adyen.NewClient`, all 15 service accessors,
  request builders and call signatures (Checkout, Transfers), `common.Config` fields,
  `APIError` and `RestServiceError` fields, nullable wrappers, `webhook.NotificationRequestItem.AdditionalData`
  as `*map[string]interface{}`, HMAC helpers, and all 15 typed webhook handlers; API version
  constants.
- `routing_test.go`: TEST and LIVE base paths for every accessor and every tag of multi-tag
  clients, and fails if an accessor is added without a routing expectation.
- `http_contract_test.go`: method, path, auth, `Idempotency-Key` (builder and deprecated
  context form), `User-Agent` and library headers, exact request body, tolerance of unknown
  response fields and enum values, `APIError` mapping for Checkout, `RestServiceError` mapping
  for Transfers.
- `json_contract_test.go`: nullable absent/null/value/empty states and setters, explicit
  `false`, discriminated `oneOf` decode, re-decode into the same destination, unknown variant
  rejection, zero amounts.
- `webhook_contract_test.go`: classic notification decode with non-string `additionalData`,
  HMAC against Adyen's published sample (computed independently with Python `hmac`),
  tampered/missing/non-string signatures, a typed payload, and malformed JSON for every
  handler.

Sensitivity check: running the fixtures against the retracted **v21.2.1** fails to compile on
`AdditionalData` (`*map[string]string`), i.e. the gate catches the change that caused the
retraction.

When the module path moves to `/v22` (increment 8), only the import paths in these files
change. Any other edit to an expectation must be recorded in the breaking-change ledger.

## Isolation of experimental generation

Rule applied in this increment: all experimental generation runs locally into a dedicated
worktree; nothing is dispatched through CI.

Risk found in `.github/workflows/gradle.yml`: generation always checks out the SDK default
branch and opens PRs from `sdk-automation/<service>` against it. A `workflow_dispatch` from a
migration branch of this repository would therefore force-update the production bot PRs.
Proposed guard (not implemented, needs approval because it changes production CI): a
`sdk_base_branch` dispatch input that sets the SDK checkout `ref`, the PR `base`, and a branch
prefix `sdk-automation/<base>/<service>` when it is not the default branch.

## Open decisions before increment 2

1. Approve or reject the CI guard above, or keep migration generation local-only.
2. Whether S1 and S3 are fixed on the v21 maintenance line or only in v22.
3. Whether to push the `go-v22-migration` branches (to `Adyen/*` or a fork).
