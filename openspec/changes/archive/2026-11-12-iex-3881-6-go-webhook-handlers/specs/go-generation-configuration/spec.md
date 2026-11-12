## MODIFIED Requirements

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
