## 1. Implementation

- [x] 1.1 Add `common.NullableSlice[T]` with JSON marshaling of absent, `null`, and set values
- [x] 1.2 Generate nullable arrays as `common.NullableSlice[T]` with `Set<Field>Nil` and `Unset<Field>`
- [x] 1.3 Regenerate all Go services and fixtures; regeneration is idempotent

## 2. Gate

- [x] 2.1 Fixture tests cover absent, `null`, empty, and set arrays in both directions
- [x] 2.2 A Management PATCH request sends `"gratuities":null` through the client
- [x] 2.3 `apidiff` against v21.2.3 shows one new incompatible change (`TerminalSettings.Gratuities`)
- [x] 2.4 `go build`, `go vet`, and `go test ./...` pass on Go 1.23.0 and the current toolchain
