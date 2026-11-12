## Context

Go generation registers `generate<Svc>`/`deploy<Svc>` per catalog entry, then patches individual
tasks by name. `additionalProperties.set(...)` in several blocks overwrites the shared
`serviceName` property, so the last writer wins.

## Goals / Non-Goals

**Goals:** a single, testable mapping from catalog entry to Go generation settings; output for
current services unchanged.

**Non-Goals:** renaming packages; changing the catalog schema; other languages.

## Decisions

- **Data-driven mapping** (a `GoServiceLayout` derived from `Service` plus a legacy-override map)
  applied in one `services.forEach`. Alternative rejected: adding Go-specific fields to
  `config/services.json` (the catalog is language-neutral and validated by CI scripts).
- **Error model from the spec.** Set `hasRestServiceError` when an operation response references
  `RestServiceError`, computed during staging or configuration from the staged spec.
  Alternative rejected: extending the hard-coded list (must be maintained per service).
- **Unit tests over runtime asserts.** Test the mapping with ProjectBuilder like
  `SdkAutomationConventionsTest`; drop the inline `assert` calls that only run with `-ea`.
- **Deploy replaces the target directory.** `deploy<Svc>` copies into the service's real directory
  (`GoServiceLayout.directory`) and first deletes its contents, keeping only `webhook_handler.go`.
  Before, Payment and LegalEntityManagement cleaned `src/payment` and `src/legalentitymanagement`
  (which do not exist) and then copied into `src/payments` and `src/legalentity`, so files from
  older generations survived: the exported but unwired `payments.GeneralApi`
  (`src/payments/api_general.go`) and `src/legalentity/api/openapi.yaml`. Both are removed by the
  next regeneration (recorded in the breaking-change ledger for v22).
- **`client.go` follows the generated APIs.** Webhooks never deploy it. Small services skip it,
  unless they generate more than one `api_*.go` file: Payment is small in the catalog but has the
  Modifications and Payments tags, and `adyen.APIClient.Payments()` returns its `APIClient`.
  Before, its `client.go` was never redeployed and only survived from an older generation.
- **Implementation.** `GoServiceLayout` (pure mapping, unit tested) and
  `Project.configureGoServices` (task wiring, tested with ProjectBuilder through the real
  conventions plugin) live in `buildSrc/src/main/kotlin/com/adyen/sdk`.

## Risks / Trade-offs

- [Mapping change silently renames a package] → regenerate all 29 services before and after and
  require an empty diff, apart from the two stale files above.
