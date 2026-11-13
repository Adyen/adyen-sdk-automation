## 1. Generation

- [x] 1.1 Generate value constants for inline enum fields, including array items
- [x] 1.2 Keep the `isValid<Field>` helpers that `oneOf` decoding relies on
- [x] 1.3 Unescape parameter descriptions in doc comments
- [x] 1.4 Use `any` in templates and map free-form types to `any`

## 2. Handwritten code

- [x] 2.1 Replace `io/ioutil` and `interface{}` in `common`, `adyen`, `hmacvalidator`
- [x] 2.2 Add `common.Ptr[T]`
- [x] 2.3 Add `Config.Logger`; print error bodies (not the reader) without a logger
- [x] 2.4 Add godoc examples for payments, errors, logging, and HMAC validation; update README

## 3. Gate

- [x] 3.1 Fixture test pins constant names for unusual values
- [x] 3.2 Tests for the logger, stdout logging, `Ptr`, and unescaped doc comments
- [x] 3.3 `apidiff` against v21.2.3 shows no new incompatible change
- [x] 3.4 Regeneration is idempotent; build, vet, and test pass on Go 1.23.0 and the current toolchain
