## Context

The Go project pins generator 6.5.0 (`go/gradle.properties`) while buildSrc uses 7.11.0; CI copies
the language properties into buildSrc. v21.2.1 was retracted after an accidental change to
`NotificationRequestItem.AdditionalData`, so compatibility must be checked mechanically.

## Goals / Non-Goals

**Goals:** a reproducible starting point; failures attributed to the right cause; a fixture suite
that catches public-surface and wire changes.

**Non-Goals:** any generator, template, or catalog change; a v21 patch release.

## Decisions

- **Fresh pinned working copies** under `go-v22-migration/` instead of the developer checkout,
  which was 40 commits behind v21.2.3 and held untracked Balance Platform files.
  Alternative rejected: cleaning the existing checkout (would destroy user work).
- **Fixtures in the SDK repository** (`tests/compat`), not in automation, so they run with
  `go test ./...` in every later increment and in SDK CI.
  Alternative rejected: golden-file diffs of generated code (too noisy to review).
- **Synthetic HMAC key built at runtime** with a signature computed independently in Python, so
  no real-looking secret is committed.
- **Local-only migration generation.** A `sdk_base_branch` workflow input was rejected: a dispatch
  from a migration branch would otherwise force-update the production bot PRs.
- **S1/S3 fixed only for v22.** S1 renames JSON keys of `common.Config`; recorded in the
  breaking-change ledger.

## Risks / Trade-offs

- [Fixtures freeze current defaults such as W1 `threeDSAuthenticationOnly=false`] → a generator
  default change shows up as a fixture failure and must be decided explicitly.
- [Bot PR backlog (#516-#609) inflates regeneration diffs] → baseline regeneration diff is
  recorded so later increments compare against it, not against v21.2.3.
