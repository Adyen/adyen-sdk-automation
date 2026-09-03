---
name: pr-notes
description: >-
  Generate PR notes for changes in an Adyen SDK language library. Use when the
  user asks to document a current SDK pull request or compare its branch with
  its default branch. Usage: /pr-notes <language> [from_ref] [to_ref].
user-invocable: true
---
# SDK PR Notes Generator

Parse `$ARGUMENTS` as: `<language> [from_ref] [to_ref]`

- `language` (required): one of `java`, `python`, `dotnet`, `go`, `node`, `php`, `ruby`
- `from_ref` (optional): PR base ref (defaults to the merge-base of `HEAD` and the default branch)
- `to_ref` (optional): PR target ref (defaults to `HEAD`)

Workflow:

1. Validate that `<language>/repo` exists.
   - If missing, stop and ask the user to clone or symlink the target SDK repository first.
2. Resolve the PR commit range:
   - If `from_ref` is omitted, find the target repository's default branch and use its merge-base with `to_ref`.
   - If `to_ref` is omitted, use `HEAD`.
3. Delegate to the `sdk-pr-notes-generator` subagent with the resolved `language`, `from_ref`, and `to_ref`.
4. Return the generated PR notes directly to the user.
