## Context

`SpecProcessor` marks webhook roots with `x-webhook-root` and marks one model with
`x-has-at-least-one-webhook-root`, because Mustache cannot detect "any model is a root" across
models. Java and other languages already generate handlers from this metadata.

## Goals / Non-Goals

**Goals:** generated handlers that match the v21 exported API; no hand-maintained handler files.

**Non-Goals:** changing the classic `webhook` package (payment notifications, HMAC);
changing `NotificationRequestItem.AdditionalData`.

## Decisions

- **Generate from existing metadata**; no new spec annotation. Alternative rejected: a handler list
  in the build script (duplicates the spec).
- **Name compatibility first.** Derive handler names from the v21 exported API; add an explicit
  name map for handlers whose names do not follow the generated pattern.
- **Switch deployment last.** Keep preserving `webhook_handler.go` until the generated handler is
  a superset of the manual one; then delete the preservation rule.

## Risks / Trade-offs

- [A manual handler contains logic beyond parsing] → diff each manual handler against the generated
  one before deleting it; port extra logic into the template or a common helper.
