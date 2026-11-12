## 1. Engine

- [ ] 1.1 Pin `go/gradle.properties` to 7.11.0 and log the loaded generator version in local runs and CI
- [ ] 1.2 Diff upstream Go templates 6.5.0 → 7.11.0 and list changes relevant to 3.1, unions, and nullables

## 2. Fixtures

- [ ] 2.1 Add fixture specs for allOf with inherited required fields, discriminated/non-discriminated oneOf, anyOf, nullable primitives/arrays/maps, defaults, and colliding enums
- [ ] 2.2 Add the real IEX-3881 models from Management and Balance Platform
- [ ] 2.3 Add a task that generates, formats (`make fmt`), builds, and tests the fixtures

## 3. Templates

- [ ] 3.1 Fix nullable type qualification (no `common.interface{}`)
- [ ] 3.2 Generate union code without assuming `isValidType()` on every member
- [ ] 3.3 Keep inherited `allOf` fields (G1)
- [ ] 3.4 Prefix colliding enum constants (G3, B1)
- [ ] 3.5 Keep v21 decoding tolerance for unknown fields and enum values

## 4. Gate

- [ ] 4.1 Fixtures format, compile, and pass on Go 1.23 and the latest Go
- [ ] 4.2 Checkout regenerates and compiles; `go test ./tests/compat/` passes
