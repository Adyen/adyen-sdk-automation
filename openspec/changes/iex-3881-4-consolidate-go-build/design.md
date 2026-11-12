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

## Risks / Trade-offs

- [Mapping change silently renames a package] → regenerate all 29 services before and after and
  require an empty diff.
