## ADDED Requirements

### Requirement: Each Go service is configured in one place
Every Go service's package name, deployment directory, `serviceName`, and generator options SHALL
be derived by a single per-service configuration path, and options set for one service MUST NOT
apply to another.

#### Scenario: Per-service options are isolated
- **WHEN** Transfers enables the error model
- **THEN** a service whose spec has no `RestServiceError` responses generates without it

### Requirement: Legacy package paths stay stable
The configuration SHALL keep `Payment` in `src/payments`, `LegalEntityManagement` in
`src/legalentity` with service name `LegalEntity`, and webhook services in their singular package
(for example `AcsWebhooks` in `src/acswebhook`).

#### Scenario: Regeneration of a legacy-named service
- **WHEN** `LegalEntityManagement` is generated and deployed
- **THEN** files land in `src/legalentity` with package `legalentity`

### Requirement: Deployment replaces generated files
Deploying a Go service SHALL replace the contents of its package directory with the generated
files, keeping only handwritten webhook handlers (`webhook_handler.go`). `client.go` SHALL be
deployed for every non-webhook service except small services that generate a single API file.

#### Scenario: Stale files from an older generation
- **WHEN** `Payment` is deployed and `src/payments` contains a file the generator no longer produces
- **THEN** that file is removed and `src/payments/client.go` is regenerated

#### Scenario: Webhook handler survives
- **WHEN** `AcsWebhooks` is deployed
- **THEN** `src/acswebhook/webhook_handler.go` is kept and no `client.go` is deployed

### Requirement: Error model follows the spec
`hasRestServiceError` SHALL be enabled exactly for services whose spec references
`RestServiceError` in an operation response.

#### Scenario: Management and Balance Platform
- **WHEN** Management or Balance Platform is generated
- **THEN** generated services map error responses to `RestServiceError`
