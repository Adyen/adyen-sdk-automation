## MODIFIED Requirements

### Requirement: Go spec staging normalizes for OpenAPI 3.1
Go spec staging SHALL remove `additionalProperties: false`, rewrite `nullable: true` to the 3.1
form, and mark `$ref` members of nullable unions; staging for other projects MUST stay unchanged.
A `nullable: true` next to a `$ref` SHALL be removed without making the reference nullable, as
OpenAPI 3.0 and 3.1 ignore `$ref` siblings.

#### Scenario: Staged specs
- **WHEN** all projects stage their specs
- **THEN** non-Go specs are byte-identical to increment 2 and Go specs equal the source plus the normalization

#### Scenario: Nullable reference sibling
- **WHEN** a property is `{"$ref": "#/components/schemas/CardholderReceipt", "nullable": true}`
- **THEN** the Go field is `*CardholderReceipt`, as in v21
