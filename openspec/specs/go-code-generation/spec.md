# go-code-generation Specification

## Purpose
Defines which OpenAPI Generator engine and templates produce the Go library, how Go specs are
normalized for native OpenAPI 3.1 generation, and how generation fixtures pin that behavior.
## Requirements
### Requirement: Go generation uses a pinned v7 engine
The Go project SHALL pin OpenAPI Generator 7.11.0 in `go/gradle.properties`, and generation MUST
report the engine version it actually loaded.

#### Scenario: CI generation
- **WHEN** the Go project generates in CI or locally
- **THEN** the log shows OpenAPI Generator 7.11.0

### Requirement: Nullable values keep their three states
Generated models SHALL distinguish absent, explicit `null`, and set values for nullable primitive
and object properties declared with `nullable: true`, a 3.1 type array containing `null`, or a
`oneOf` with a `null` member. Nullable arrays and maps MUST keep the v21 behavior: absent and
explicit `null` both decode to `nil`.

#### Scenario: Round trip of an explicit null
- **WHEN** a JSON payload sets a nullable integer to `null` and is decoded and re-encoded
- **THEN** the output contains the property with value `null`

#### Scenario: Absent value
- **WHEN** the property is absent in the payload
- **THEN** it is absent after re-encoding

#### Scenario: Non-nullable reference to a schema used nullably elsewhere
- **WHEN** one property references `Amount` through a nullable union and another references it plainly
- **THEN** only the first property is generated as `NullableAmount`

### Requirement: Composed schemas compile and decode
Generated code SHALL compile and decode correctly for `allOf` (including inherited required
fields), discriminated and non-discriminated `oneOf`, and `anyOf`.

#### Scenario: Inherited required field
- **WHEN** a schema is `allOf` of a base with a required `type` and an extension
- **THEN** the generated struct contains `Type` and its constructor sets it

#### Scenario: Unknown discriminator value
- **WHEN** a discriminated `oneOf` payload carries an unknown discriminator value
- **THEN** decoding returns an error rather than a partially filled variant

### Requirement: Enum constants never collide
Generated enum constants in one package MUST be unique: constants of top-level enum types SHALL be
prefixed with their type name, and constants that exist in v21.2.3 keep their names.

#### Scenario: Capital bank account types
- **WHEN** Capital is generated with `CALocalBankAccountType` and `USLocalBankAccountType`
- **THEN** the package compiles

### Requirement: Typed maps stay pointers
Optional properties with `additionalProperties` of a given type SHALL be generated as
`*map[string]T`, as in v21; free-form objects stay `map[string]interface{}`.

#### Scenario: Optional metadata map
- **WHEN** an optional property is `{type: object, additionalProperties: {type: string}}`
- **THEN** the field type is `*map[string]string`

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

### Requirement: Multipart operations send their form
Operations whose request body is `multipart/form-data` SHALL send every set form field and file
as a multipart body with the matching `Content-Type` boundary; other operations SHALL keep sending
JSON.

#### Scenario: Document upload
- **WHEN** `UploadCrossBorderInvoice` is called with a context, merchant account, and PDF file
- **THEN** the server receives a multipart form with both fields and the file under its base name

