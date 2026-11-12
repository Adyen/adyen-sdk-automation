## Why

Go webhook handlers are written by hand: deployment deletes every file in a webhook package except
`webhook_handler.go`, and no template creates a missing handler (for example relayed
authorisation). New or changed webhook specs therefore need manual work. Increment 2 already
stages the `x-webhook-root` metadata for Go. Increment 6 of 8.

## What Changes

- Add a Go supporting-file template that generates typed parsing helpers for every
  `x-webhook-root` model, including the special roots (`RelayedAuthenticationRequest`,
  `DisputeNotificationRequest`, `RelayedAuthorisationRequest`).
- Keep the exported handler names of v21.
- Replace the "preserve `webhook_handler.go`" deployment rule only after the generated handlers
  cover every existing handler.
- Add payload and malformed-JSON tests for every handler; keep classic payment webhook and HMAC
  behavior unchanged.

## Capabilities

### New Capabilities
- `go-webhook-handlers`: generated typed webhook handlers for Go.

### Modified Capabilities
- `go-generation-configuration`: webhook packages render their handler instead of keeping a
  handwritten one; generation starts from an empty output directory.

## Impact

- Go SDK `templates/custom` and `templates/config.yaml`; `GoServiceLayout`/`GoServices` deployment rules;
  `tests/compat/webhook_contract_test.go` remains the gate.
- Gate: clean regeneration produces all applicable handlers without manual restoration, and a
  second run leaves no substantive diff.
