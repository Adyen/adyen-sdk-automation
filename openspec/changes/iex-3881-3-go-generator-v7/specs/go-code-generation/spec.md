## ADDED Requirements

### Requirement: Go generation uses a pinned v7 engine
The Go project SHALL pin OpenAPI Generator 7.11.0 in `go/gradle.properties`, and generation MUST
report the engine version it actually loaded.

#### Scenario: CI generation
- **WHEN** the Go project generates in CI or locally
- **THEN** the log shows OpenAPI Generator 7.11.0

### Requirement: Nullable values keep their three states
Generated models SHALL distinguish absent, explicit `null`, and set values for nullable properties
declared either with `nullable: true` or with a 3.1 type array containing `null`, for primitives,
arrays, maps, and objects.

#### Scenario: Round trip of an explicit null
- **WHEN** a JSON payload sets a nullable integer to `null` and is decoded and re-encoded
- **THEN** the output contains the property with value `null`

#### Scenario: Absent value
- **WHEN** the property is absent in the payload
- **THEN** it is absent after re-encoding

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
Generated enum constants in one package MUST be unique; when two enums would emit the same
constant name, the constants SHALL be prefixed with their type name, and non-colliding constants
keep their current names.

#### Scenario: Capital bank account types
- **WHEN** Capital is generated with `CALocalBankAccountType` and `USLocalBankAccountType`
- **THEN** the package compiles
