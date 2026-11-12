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
## Increment 5: regenerated services, Management and Balance Platform restored

Full `apidiff` reports against v21.2.3 are in [`apidiff/`](apidiff/) (one file per package with
changes). Packages not listed there have no exported change. All changes below come from the
specs unless the cause says otherwise; for every package except Management and Balance Platform
this was confirmed by `apidiff` against the 6.5.0 regeneration of the same specs (zero generator
changes). Management and Balance Platform had no 6.5.0 regeneration (excluded from Go); their
changes were checked against the source specs.

| Package | Incompatible | Main changes | Cause |
|---------|--------------|--------------|-------|
| `adyen` | 1 | `CheckoutAPIVersion` is `"v72"` (was `"v71"`): Checkout requests go to `/checkout/v72` | catalog version |
| `checkout` | 53 | `ShopperName` replaces `Name` on `PaymentRequest`, `CreateCheckoutSession*`, `DonationPaymentRequest`; `DonationPaymentRequest` loses `AdditionalData`, `ConversionId`, `DeliverAt`, `ThreeDSAuthenticationOnly`, and `PaymentMethod` becomes optional; `PaymentRequest.ConversionId` removed; `CardDetailsRequest.CardNumber`, `Donation.DonationType`, `SepaDirectDebitDetails.Iban`/`OwnerName`, `UpiCollectDetails.BillingSequenceNumber` become optional (pointer) with matching constructor changes; `SessionResultResponse` is no longer comparable | spec |
| `legalentity` | 4 | `FinancialReport.DateOfFinancialData` and `SoleProprietorship.CountryOfGoverningLaw` become optional, constructors change | spec |
| `transfers` | 13 | `Counterparty` removed; `CapitalGrant.Counterparty` is `*GrantCounterparty`, `CapitalGrantInfo.Counterparty` is `*GrantInfoCounterparty` (no `AccountHolderId`); new `CashOutApi` | spec |
| `payments` | 6 | `GeneralApi` and `GeneralApi*Input` removed (see increment 4) | generator (deployment) |
| `balanceplatform` | 62 | Sweep operations (`CreateSweep`, `GetSweep`, `GetAllSweepsForBalanceAccount`, `UpdateSweep`, `DeleteSweep` and their inputs) move from `BalanceAccountsApi` to the new `CustomPayoutSchedulesSweepsApi` (spec tag "Custom payout schedules (sweeps)"); `DeviceInfo` keeps only `FormFactor`, `OsName`, `Phone`; `Card.Number` becomes optional | spec |
| `management` | 284 | `PaymentMethod` fields and getters use the new `*ResponseInfo` types and `UpdatePaymentMethodInfo` the new `*UpdateInfo` types (228 of the 284; for example `GetApplePayDomains` returns `ApplePayResponseInfo`); `PayByBankPlaidInfo` keeps only `Logo` and `TransactionDescription`; `OfflineProcessing.OfflineSwipeLimits` removed; `AccelInfo`/`NyceInfo`/`PulseInfo`/`StarInfo.ProcessingType` become optional; `SplitConfigurationRule.FundingSource` becomes required; `Terminal` is no longer comparable | spec |
| `acswebhook` | 1 | `NewRelayedAuthenticationRequest` takes the newly required fields | spec |
| `configurationwebhook` | 2 | `Card.Number` becomes optional | spec |

Compatible additions (new fields, models, operations, enum values) are in the same reports, for
example 1127 in Checkout and 1032 in Management.

### Decisions

- `nullable: true` next to a `$ref` is ignored in Go spec staging, as OpenAPI 3.0 and 3.1 and the
  other SDKs do. Management `TerminalSettings` sections therefore stay `*CardholderReceipt` and so
  on, as in v21, instead of becoming `NullableCardholderReceipt` (21 avoided breaking changes).
  The PATCH terminal settings endpoints do not use explicit `null` for sections.
- Generated `GetXxxOk` methods no longer contain blank lines (template whitespace fix).

## Increment 6: generated webhook handlers

Every webhook package's `webhook_handler.go` is now generated from the `x-webhook-root` models of
its spec (template `templates/custom/webhook_handler.mustache`). All 36 roots get a
`Handle<Model>(req string) (*<Model>, error)` function. The 19 v21.2.3 handlers keep their names
and signatures; only their doc comments change. The classic `webhook` package and
`hmacvalidator` are unchanged.

| Package | Change | Cause | Compatibility |
|---------|--------|-------|---------------|
| `acswebhook` | `HandleRelayedAuthenticationRequest` added | generator (template) | Additive |
| `balancewebhook` | `HandleReleasedBlockedBalanceNotificationRequest` added | generator (template) | Additive |
| `configurationwebhook` | Handlers added for `AccountPayoutAutoApplication`, `Mandate`, `NetworkToken`, `PayoutScheduleBA`, `PayoutScheduleBP`, `PayoutScheduleState`, `Score`, `SweepExecution` notification requests and `TopUpConfigurationEventRequest`, `TopUpConfigurationUpdatedEventRequest` | generator (template) | Additive |
| `managementwebhook` | `HandleTerminalBoardingNotificationRequest`, `HandleTerminalSettingsNotificationRequest` added | generator (template) | Additive |
| `disputewebhook`, `negativebalancewarningwebhook`, `relayedauthorizationwebhook`, `tokenizationwebhook` | First handlers: `HandleDisputeNotificationRequest`, `HandleNegativeBalanceCompensationWarningNotificationRequest`, `HandleRelayedAuthorisationRequest`, and the four `HandleTokenization*DetailsNotificationRequest` | generator (template) | Additive |
| `checkout` | `PayToPaymentMethodAllOf`, `UPIPaymentMethodAllOf` (and their constructors and `Nullable*` types), added in increment 5, are removed again | generator (deployment) | Not in v21.2.3; unused leftovers of an earlier generation |

### Decisions

- Generation now deletes the generator output directory before each Go service run. The
  increment 5 regeneration reused an existing output directory, so two models from an earlier
  generation were deployed; a regeneration from an empty output directory no longer produces them.
- Webhook packages render `webhook_handler.go` as their only supporting file; other services keep
  rendering `client.go`. Deployment no longer keeps any handwritten file.
- Empty directories created by the generator (`api/`) are not deployed.
