## 1. Mapping

- [ ] 1.1 Introduce one per-service Go configuration (package, directory, serviceName, small/webhook deployment rules)
- [ ] 1.2 Keep the legacy overrides for Payment, LegalEntityManagement, Payout, and singular webhook packages
- [ ] 1.3 Derive `hasRestServiceError` from spec responses

## 2. Tests

- [ ] 2.1 buildSrc tests for small, multi-tag, webhook, and legacy-named services
- [ ] 2.2 Test that one service's options never appear on another service's task
- [ ] 2.3 Remove the inline `doLast` asserts

## 3. Gate

- [ ] 3.1 Regenerate all current Go services before and after; diff is empty
- [ ] 3.2 `./gradlew :buildSrc:test` passes
