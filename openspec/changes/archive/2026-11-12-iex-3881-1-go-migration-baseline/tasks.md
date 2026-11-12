## 1. Baseline

- [x] 1.1 Create pinned working copies of automation (ae7e576), adyen-openapi (d449f090), and the Go SDK (v21.2.3)
- [x] 1.2 Run buildSrc, CI script, SDK build/vet/test checks and record the results
- [x] 1.3 Regenerate all 29 Go services with 6.5.0 and record the failures
- [x] 1.4 Reproduce the PR #525 (Capital) Go 1.23 failure

## 2. Compatibility fixtures

- [x] 2.1 Add surface, routing, HTTP contract, JSON contract, and webhook fixtures in `tests/compat`
- [x] 2.2 Verify the fixtures fail against the retracted v21.2.1
- [x] 2.3 Fix S1, S2, S3 on `feature/go-generator-upgrade` and push

## 3. Decisions and gate

- [x] 3.1 Record the failure inventory and decisions in `docs/go-v22-migration/01-baseline.md`
- [x] 3.2 Gate: fixtures pass on Go 1.23-1.27.3; inventory reviewed
