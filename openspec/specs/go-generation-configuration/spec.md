# go-generation-configuration Specification

## Purpose
Defines how each catalog service maps to its Go package, directory, generator options, and
deployment rules.
## Requirements
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
Each Go service SHALL be generated into an empty output directory, and deploying it SHALL replace
the contents of its package directory with the generated files, without empty directories.
Webhook packages SHALL render `webhook_handler.go` as their only supporting file and no
`client.go`. `client.go` SHALL be deployed for every non-webhook service except small services that
generate a single API file.

#### Scenario: Stale files from an older generation
- **WHEN** `Payment` is deployed and `src/payments` contains a file the generator no longer produces
- **THEN** that file is removed and `src/payments/client.go` is regenerated

#### Scenario: Stale generator output
- **WHEN** a model was produced by an earlier generation run but is no longer in the spec
- **THEN** the next generation does not deploy it

#### Scenario: Webhook handler is generated
- **WHEN** `AcsWebhooks` is deployed
- **THEN** `src/acswebhook/webhook_handler.go` is the generated handler and no `client.go` is deployed

### Requirement: Error model follows the spec
`hasRestServiceError` SHALL be enabled exactly for services whose spec references
`RestServiceError` in an operation response.

#### Scenario: Management and Balance Platform
- **WHEN** Management or Balance Platform is generated
- **THEN** generated services map error responses to `RestServiceError`

