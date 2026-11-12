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
- **Name compatibility first.** All 19 v21 handlers are named `Handle<Model>` after their root
  model, so the template needs no name map.
- **One supporting file per service.** `GoServiceLayout.supportingFile` selects
  `webhook_handler.go` for webhook packages and `client.go` otherwise, through the generator's
  `supportingFiles` global property; the preservation rule is gone.
- **Generate into an empty directory.** The generator never deletes outputs, so stale files of
  earlier runs reached deployment (two Checkout `*AllOf` models in increment 5).

## Risks / Trade-offs

- [A manual handler contains logic beyond parsing] → diff each manual handler against the generated
  one before deleting it; port extra logic into the template or a common helper.
