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

### Requirement: Error model follows the spec
`hasRestServiceError` SHALL be enabled exactly for services whose spec references
`RestServiceError` in an operation response.

#### Scenario: Management and Balance Platform
- **WHEN** Management or Balance Platform is generated
- **THEN** generated services map error responses to `RestServiceError`
