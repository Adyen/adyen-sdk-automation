## Why

The generated Go code works but reads like generated code: fields with a fixed set of values have
no constants, doc comments contain HTML entities, the code uses `interface{}` and the deprecated
`io/ioutil`, pointer helpers need one function per type, and the SDK's logs cannot be routed to the
application's logger. pkg.go.dev shows no examples. Part of the v22 migration, before increment 8.

## What Changes

- Generate a string constant per allowed value of every inline enum field, named after the model,
  the field, and the value in Go case (`PaymentRequestShopperInteractionEcommerce`).
- Stop HTML-escaping parameter descriptions in doc comments.
- Use `any` and `io` in templates and handwritten code; map the generator's free-form types to `any`.
- Add `common.Ptr[T]` and an optional `common.Config.Logger` (`*slog.Logger`). Without a logger,
  error-response logging prints the body (it printed the reader's address).
- Add runnable godoc examples to the `adyen` and `hmacvalidator` packages.
- Keep the `isValid<Field>` helpers: `oneOf` decoding uses `isValidType` through an interface.

## Capabilities

### Modified Capabilities
- `go-code-generation`: inline enum constants and unescaped doc comments.
- `go-api-client-wiring`: configurable logger and runnable examples.

## Impact

- Go SDK templates and `config.yaml`, `src/common`, examples in `src/adyen` and
  `src/hmacvalidator`, README, tests; all generated packages (additions only).
- Automation: generation fixture spec gains an enum with unusual values.
