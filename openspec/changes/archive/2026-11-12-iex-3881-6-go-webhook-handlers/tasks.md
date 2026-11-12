## 1. Template

- [x] 1.1 Inventory v21 handler names and signatures for every webhook package
- [x] 1.2 Add the handler supporting-file template driven by `x-webhook-root`
- [x] 1.3 Cover special roots, including relayed authorisation

## 2. Deployment

- [x] 2.1 Compare generated and manual handlers; port any extra logic
- [x] 2.2 Remove the preserve-`webhook_handler.go` rule

## 3. Gate

- [x] 3.1 Clean regeneration of all webhook services produces every handler; `go test ./tests/compat/` passes
- [x] 3.2 A second regeneration leaves no diff
