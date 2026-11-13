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
- **WHEN** one service sets a generator option
- **THEN** no other service is generated with it

### Requirement: Legacy package paths stay stable
The configuration SHALL deploy each package to a directory at the repository root named after the
package, keep `Payment` in `payments`, `LegalEntityManagement` in `legalentity` with service name
`LegalEntity`, and webhook services in their singular package (for example `AcsWebhooks` in
`acswebhook`). A generated package MUST NOT use the name of a handwritten directory (`adyen`,
`common`, `webhook`, `hmacvalidator`, `templates`, `tests`).

#### Scenario: Regeneration of a legacy-named service
- **WHEN** `LegalEntityManagement` is generated and deployed
- **THEN** files land in `legalentity` with package `legalentity`

### Requirement: Deployment replaces generated files
Each Go service SHALL be generated into an empty output directory, and deploying it SHALL replace
the contents of its package directory with the generated files, without empty directories.
Webhook packages SHALL render `webhook_handler.go` as their only supporting file and no
`client.go`. `client.go` SHALL be deployed for every non-webhook service except small services that
generate a single API file.

#### Scenario: Stale files from an older generation
- **WHEN** `Payment` is deployed and `payments` contains a file the generator no longer produces
- **THEN** that file is removed and `payments/client.go` is regenerated

#### Scenario: Stale generator output
- **WHEN** a model was produced by an earlier generation run but is no longer in the spec
- **THEN** the next generation does not deploy it

#### Scenario: Webhook handler is generated
- **WHEN** `AcsWebhooks` is deployed
- **THEN** `acswebhook/webhook_handler.go` is the generated handler and no `client.go` is deployed

