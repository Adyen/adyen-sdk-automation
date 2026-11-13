## MODIFIED Requirements

### Requirement: Enum constants never collide
Generated enum constants in one package MUST be unique: every enum constant SHALL be named after
its enum type and the value in Go case, without the generator's upper-case type prefix
(`CalculationTypeLRSTCS`), and constants that exist in v21.2.3 keep their names.

#### Scenario: Capital bank account types
- **WHEN** Capital is generated with `CALocalBankAccountType` and `USLocalBankAccountType`
- **THEN** the package compiles with `CALocalBankAccountTypeChecking` and `USLocalBankAccountTypeChecking`

### Requirement: Inline enum values have constants
Every model field whose schema lists allowed values inline SHALL have a named string type
`<Model><Field>` (array items included) with one constant per value, named after the type and the
value converted to Go case, with the value's own casing kept. Decoding SHALL accept values that are
not in the spec; `IsValid()` SHALL report whether a value is a known constant.

#### Scenario: Shopper interaction
- **WHEN** `PaymentRequest.shopperInteraction` allows `Ecommerce` and `POS`
- **THEN** `SetShopperInteraction` takes a `PaymentRequestShopperInteraction` and `PaymentRequestShopperInteractionEcommerce` and `PaymentRequestShopperInteractionPOS` exist

#### Scenario: Values with separators
- **WHEN** a value contains `,` or `/`, as in `ONECLICK,RECURRING` or `application/pdf`
- **THEN** the separator is dropped from the constant name

#### Scenario: Unknown value in a response
- **WHEN** a response carries a value added to the API after this SDK version
- **THEN** it decodes, re-encodes unchanged, and `IsValid()` returns false
