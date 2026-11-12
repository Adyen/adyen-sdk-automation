## 1. Engine

- [x] 1.1 Pin `go/gradle.properties` to 7.11.0 and log the loaded generator version in local runs and CI
- [x] 1.2 Diff upstream Go templates 6.5.0 → 7.11.0 and list changes relevant to 3.1, unions, and nullables

## 2. Fixtures

- [x] 2.1 Add fixture specs for allOf with inherited required fields, discriminated/non-discriminated oneOf, anyOf, nullable primitives/arrays/maps, defaults, and colliding enums
- [x] 2.2 Add the real IEX-3881 models from Management and Balance Platform (trial generation of both full specs: builds, `tests/management` and `tests/compat` pass; committed regeneration is increment 5)
- [x] 2.3 Add a task that generates, formats (`make fmt`), builds, and tests the fixtures (`./gradlew :go:fixtures`, then the SDK's `make fmt` and `go test ./...`)

## 3. Templates

- [x] 3.1 Fix nullable type qualification (no `common.interface{}`)
- [x] 3.2 Generate union code without assuming `isValidType()` on every member
- [x] 3.3 Keep inherited `allOf` fields (G1)
- [x] 3.4 Prefix colliding enum constants (G3, B1)
- [x] 3.5 Keep v21 decoding tolerance for unknown fields and enum values

## 4. Gate

- [x] 4.1 Fixtures format, compile, and pass on Go 1.23 and the latest Go
- [x] 4.2 Checkout regenerates and compiles; `go test ./tests/compat/` passes
- [x] 4.3 Staged specs: non-Go byte-identical to increment 2; Go equals the source plus the 3.1 normalization
- [x] 4.4 `apidiff` against a 6.5.0 regeneration of the same specs: no incompatible change except new-to-v22 Checkout enum constants
