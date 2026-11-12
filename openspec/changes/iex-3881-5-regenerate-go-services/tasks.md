## 1. Regeneration batches

- [ ] 1.1 Small API (e.g. BinLookup)
- [ ] 1.2 Checkout (update the API-version constant to v72)
- [ ] 1.3 Legal Entity Management
- [ ] 1.4 Transfers
- [ ] 1.5 Management and Balance Platform (generated, not yet in the catalog)
- [ ] 1.6 Remaining existing services

## 2. Catalog

- [ ] 2.1 Remove the Go exclusion for Management and Balance Platform
- [ ] 2.2 Update `.github/scripts` and buildSrc test expectations (31 Go entries)
- [ ] 2.3 Add routing expectations for the restored accessors in `tests/compat`

## 3. Ledger

- [ ] 3.1 Create the breaking-change ledger and record every public change per batch

## 4. Gate

- [ ] 4.1 `./gradlew -DopenapiGeneratorVersion=7.11.0 :go:services` then `make fmt`; `go build`, `go test ./...` pass
- [ ] 4.2 `python3.12 -m unittest discover -s .github/scripts` and `./gradlew :buildSrc:test` pass
