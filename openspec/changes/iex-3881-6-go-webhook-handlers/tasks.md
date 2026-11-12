## 1. Template

- [ ] 1.1 Inventory v21 handler names and signatures for every webhook package
- [ ] 1.2 Add the handler supporting-file template driven by `x-webhook-root`
- [ ] 1.3 Cover special roots, including relayed authorisation

## 2. Deployment

- [ ] 2.1 Compare generated and manual handlers; port any extra logic
- [ ] 2.2 Remove the preserve-`webhook_handler.go` rule

## 3. Gate

- [ ] 3.1 Clean regeneration of all webhook services produces every handler; `go test ./tests/compat/` passes
- [ ] 3.2 A second regeneration leaves no diff
