---
name: release
description: >-
  Generate release notes for an Adyen SDK language library. Usage: /release
  <language> [from_version] [to_version]. Compares latest released tag to HEAD
  when versions are omitted.
---
# Release Notes Generator

Parse `$ARGUMENTS` as: `<language> [from_version] [to_version]`

- `language` (required): one of `java`, `python`, `dotnet`, `go`, `node`, `php`, `ruby`
- `from_version` (optional): baseline tag, e.g. `v41.0.0` (defaults to latest released tag)
- `to_version` (optional): target tag/branch/commit (defaults to `HEAD`)

Workflow:

1. Validate that `<language>/repo` exists.
   - If missing, stop and ask the user to clone or symlink the target SDK repository first.
2. Resolve version range:
   - If versions are omitted, compare latest released tag to `HEAD`.
   - If only `from_version` is provided, compare `from_version` to `HEAD`.
3. Delegate to the `sdk-release-notes-generator` subagent using the resolved inputs.
4. Return the generated release notes directly to the user.
