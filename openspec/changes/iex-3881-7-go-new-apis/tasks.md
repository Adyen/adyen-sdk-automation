## 1. Per API (Capital, SessionAuthentication, ForeignExchange, DocumentCollector, SoftPOSConfiguration)

- [ ] 1.1 Generate from the pinned spec; `make fmt`; build
- [ ] 1.2 Add `common.Config` endpoint field, TEST/LIVE routing, and `adyen.APIClient` accessor
- [ ] 1.3 Add the API-version constant, request/response tests, README entry, routing fixture

## 2. Specific fixes

- [ ] 2.1 Fix Document Collector `DocumentContext` and multipart imports (G2)
- [ ] 2.2 Decide and document Capital vs `transfers.CapitalApi` (S4)
- [ ] 2.3 Audit existing generated services (PosMobile) for missing wiring
- [ ] 2.4 Check idempotency headers against the specs; track PF-3045

## 3. Gate

- [ ] 3.1 Each API is callable through `adyen.NewClient(...).<Api>()` against a mock server in tests
- [ ] 3.2 `go test ./...` and `go test ./tests/compat/` pass
