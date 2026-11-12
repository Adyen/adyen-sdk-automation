# Go v22 breaking-change ledger

Every change to an exported identifier or to wire behavior between v21.2.3 and v22 is listed here
with its cause (`generator` = engine, template, or spec staging; `spec` = OpenAPI spec content).
Migration notes for the release (increment 8) are written from this file.

Evidence: `apidiff` against a 6.5.0 regeneration of the same specs isolates generator changes;
`apidiff` against v21.2.3 shows the full public change.

## Increment 3: generator 7.11.0 and templates

| Area | Change | Cause | Compatibility |
|------|--------|-------|---------------|
| All discriminated `oneOf` types (e.g. `checkout.CheckoutPaymentMethod`) | Decoding selects the variant by the spec's discriminator mapping values (`scheme`, `ideal`, `iban`, ...); model names are still accepted | generator | Wire: payloads that 6.5.0 regeneration could not decode now decode; v21.2.3 matched structurally |
| All discriminated `oneOf` types | Decoding into a value that already holds a variant clears it first; an unknown discriminator value returns an error and leaves no variant set | generator (template) | Same observable behavior as v21.2.3 (`tests/compat`) |
| Nullable array/map fields | `Has<Field>()` returns `true` only when the field is set (v21 returned `true` when it was `nil`) | generator (template, upstream 7.x fix) | Behavior change |
| `checkout.PayToPaymentMethod`, `checkout.UPIPaymentMethod` | Gain the inherited `Type` field and accessors (G1) | generator | Additive; types are new since v21.2.3 |
| New top-level enum types (Checkout `CalculationType`, `RemittancePurpose`, `Result`, `SublimitStatus`, `TaxIdentificationType`; Capital; Balance Platform) | Constants are prefixed with the type name (`CALCULATIONTYPE_LRS_TCS`) | generator (`enumClassPrefix`) | No v21.2.3 constant changes; these types are new |
| Generated doc comments | Descriptions next to `$ref` properties and `x-deprecatedInVersion` messages now appear | generator | Documentation only |

No exported identifier changed between the 6.5.0 and 7.11.0 regenerations of the same specs
except the Checkout enum constants above (`apidiff`, 30 packages).

### Known limitation kept from v21

Nullable arrays and maps are plain slices and maps: absent and explicit `null` both decode to `nil`,
and an explicit `null` cannot be sent. Affected PATCH models arrive with increment 5 (Management
donation settings, Balance Platform `BalanceWebhookSettingInfoUpdate.conditions`).

## Increment 4: Go build consolidation

| Area | Change | Cause | Compatibility |
|------|--------|-------|---------------|
| `payments.GeneralApi` and its `GeneralApi*Input` types | Removed. The file `src/payments/api_general.go` came from an older generation, was never wired into `payments.APIClient`, and was kept only because deployment cleaned the wrong directory. The same operations stay on `payments.PaymentsApi` (`Authorise`, `Authorise3d`, `Authorise3ds2`, `GetAuthenticationResult`, `Retrieve3ds2Result`) | generator (deployment) | Breaking for code that referenced the type; use `client.Payments().PaymentsApi` |
| `src/legalentity/api/openapi.yaml` | Removed (stale spec copy from an older generation, not used by any Go code) | generator (deployment) | No API change |
## Spec changes seen while regenerating (owned by increment 5)

| Package | Change | Cause |
|---------|--------|-------|
| `transfers` | `Counterparty` removed; `CapitalGrantInfo.Counterparty` is now `*GrantInfoCounterparty`, which has no `AccountHolderId` | spec |
| `checkout` | 53 incompatible changes against v21.2.3 (for example `ShopperName` replaces `Name` on requests, `DonationPaymentRequest` fields removed, several fields no longer required) | spec |
