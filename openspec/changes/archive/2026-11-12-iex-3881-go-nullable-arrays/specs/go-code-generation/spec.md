## MODIFIED Requirements

### Requirement: Nullable values keep their three states
Generated models SHALL distinguish absent, explicit `null`, and set values for nullable primitive,
object, and array properties declared with `nullable: true`, a 3.1 type array containing `null`, or
a `oneOf` with a `null` member. Nullable arrays SHALL be generated as `common.NullableSlice[T]`,
whose zero value is absent, with `Set<Field>Nil()` and `Unset<Field>()` accessors; an empty array
MUST stay distinct from `null`. Nullable maps MUST keep the v21 behavior: absent and explicit `null`
both decode to `nil`.

#### Scenario: Round trip of an explicit null
- **WHEN** a JSON payload sets a nullable integer to `null` and is decoded and re-encoded
- **THEN** the output contains the property with value `null`

#### Scenario: Absent value
- **WHEN** the property is absent in the payload
- **THEN** it is absent after re-encoding

#### Scenario: Non-nullable reference to a schema used nullably elsewhere
- **WHEN** one property references `Amount` through a nullable union and another references it plainly
- **THEN** only the first property is generated as `NullableAmount`

#### Scenario: Clearing a nullable array
- **WHEN** a client calls `SetGratuitiesNil()` on `management.TerminalSettings` and sends the PATCH request
- **THEN** the request body contains `"gratuities":null`

#### Scenario: Empty nullable array
- **WHEN** a nullable array is set to an empty slice
- **THEN** it is encoded as `[]`, not `null`, and decodes back to a set, empty value
