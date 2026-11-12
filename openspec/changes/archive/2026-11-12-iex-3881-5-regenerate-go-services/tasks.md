## 1. Regeneration batches

- [x] 1.1 Small API (BinLookup)
- [x] 1.2 Checkout (update the API-version constant to v72)
- [x] 1.3 Legal Entity Management
- [x] 1.4 Transfers
- [x] 1.5 Management and Balance Platform
- [x] 1.6 Remaining existing services

## 2. Catalog

- [x] 2.1 Remove the Go exclusion for Management and Balance Platform
- [x] 2.2 Update `.github/scripts` and buildSrc test expectations (31 Go entries)
- [x] 2.3 Routing expectations for the restored accessors in `tests/compat` (already present from v21; every tag, including new ones such as `CashOutApi`, is checked by reflection)

## 3. Ledger

- [x] 3.1 Record every public change per batch in the breaking-change ledger, with `apidiff` reports in `docs/go-v22-migration/apidiff/`

## 4. Gate

- [x] 4.1 `./gradlew :go:services` (7.11.0 from `go/gradle.properties`) then `make fmt`; `go build`, `go vet`, `go test ./...` pass on Go 1.23 and 1.27
- [x] 4.2 `python3.12 -m unittest discover -s .github/scripts` and `./gradlew :buildSrc:test` pass
