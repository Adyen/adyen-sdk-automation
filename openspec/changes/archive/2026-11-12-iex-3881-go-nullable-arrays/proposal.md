## Why

Nullable arrays were plain slices: absent and explicit `null` both decoded to `nil`, and a client
could not send `null` to clear a list in a PATCH request. Eight PATCH request fields in Management
and Balance Platform declare nullable arrays. Part of the v22 migration (between increments 7 and 8).

## What Changes

- Add `common.NullableSlice[T]`: zero value means absent, `Set(nil)` sends `null`, `Set(v)` sends `v`.
- Generate nullable array properties as `common.NullableSlice[T]` with `Set<Field>Nil()` and
  `Unset<Field>()` accessors. Getters keep returning `[]T`.
- **BREAKING**: `management.TerminalSettings.Gratuities` changes type (the only affected field that
  exists in v21.2.3). The other seven fields are on models that are new in v22.
- Nullable maps are unchanged (no current spec declares one; pointer-to-map types stay).

## Capabilities

### Modified Capabilities
- `go-code-generation`: nullable arrays keep their three states.

## Impact

- Go SDK `templates/custom/model_simple.mustache`, `src/common/utils.go`, six generated models,
  generation fixtures, tests.
- Ledger: one breaking field type for v21 users.
