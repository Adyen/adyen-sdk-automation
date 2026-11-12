## ADDED Requirements

### Requirement: Webhook handlers are generated
For each webhook service, generation SHALL produce a handler that parses every `x-webhook-root`
model of that spec into its typed struct, without any manually maintained file.

#### Scenario: Clean regeneration
- **WHEN** a webhook package is deleted and regenerated
- **THEN** its handler file exists and the package compiles

#### Scenario: Malformed payload
- **WHEN** a handler receives malformed JSON
- **THEN** it returns an error and no partially filled struct

### Requirement: Handler API stays compatible
Generated handlers SHALL keep the exported names and signatures of the v21 handlers, and the
classic payment webhook and HMAC helpers MUST behave as in v21.

#### Scenario: Compat fixtures
- **WHEN** `go test ./tests/compat/` runs against generated handlers
- **THEN** every webhook fixture passes unchanged

### Requirement: Generation is idempotent
Regenerating webhook packages twice from the same specs SHALL produce no diff.

#### Scenario: Second run
- **WHEN** webhook services are generated twice in a row
- **THEN** `git status` shows no changes after the second run
