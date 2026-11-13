## ADDED Requirements

### Requirement: Inline enum values have constants
Every model field whose schema lists allowed values inline SHALL get one constant per value, named
after the model, the field, and the value converted to Go case, with the value's own casing kept.
Field types MUST stay unchanged.

#### Scenario: Shopper interaction
- **WHEN** `PaymentRequest.shopperInteraction` allows `Ecommerce` and `POS`
- **THEN** `PaymentRequestShopperInteractionEcommerce` and `PaymentRequestShopperInteractionPOS` exist and `SetShopperInteraction` still takes a `string`

#### Scenario: Values with separators
- **WHEN** a value contains `,` or `/`, as in `ONECLICK,RECURRING` or `application/pdf`
- **THEN** the separator is dropped from the constant name

### Requirement: Doc comments are plain Go text
Generated doc comments SHALL NOT contain HTML entities such as `&#x60;` or `&quot;`.

#### Scenario: Parameter description with backticks
- **WHEN** a parameter description contains backticks
- **THEN** the generated comment contains the backticks
