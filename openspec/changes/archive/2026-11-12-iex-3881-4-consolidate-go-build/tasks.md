## 1. Mapping

- [x] 1.1 Introduce one per-service Go configuration (package, directory, serviceName, small/webhook deployment rules)
- [x] 1.2 Keep the legacy overrides for Payment, LegalEntityManagement, Payout, and singular webhook packages
- [x] 1.3 Derive `hasRestServiceError` from spec responses
- [x] 1.4 Deploy each service into its real target directory, replacing its previous contents except handwritten webhook handlers

## 2. Tests

- [x] 2.1 buildSrc tests for small, multi-tag, webhook, and legacy-named services
- [x] 2.2 Test that one service's options never appear on another service's task
- [x] 2.3 Remove the inline `doLast` asserts

## 3. Gate

- [x] 3.1 Regenerate all current Go services before and after; the only differences are the agreed stale-file removals (`payments/api_general.go`, `legalentity/api/openapi.yaml`)
- [x] 3.2 `./gradlew :buildSrc:test` passes
