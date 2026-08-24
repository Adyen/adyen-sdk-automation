---
name: release-notes-generation
description: >-
  Generate comprehensive, evidence-backed release notes for an Adyen API
  library by invoking the release-notes-generation-droid. Usage:
  /release-notes-generation <language> [from_version] [to_version]. The source
  library is cloned temporarily; outputs are written to the invocation directory.
---
# Adyen API Libraries Release Notes Generation

This skill owns user interaction, argument validation, invocation-directory
resolution, overwrite authorization, delegation, and final result reporting.
The `release-notes-generation-droid` owns source acquisition, repository and
language validation, range resolution, defensive input verification, release
analysis, composition, reconciliation, validation, artifact writing, artifact
read-back verification, and temporary-clone cleanup.

## Arguments

Parse `$ARGUMENTS` as: `<language> [from_version] [to_version]`

- `language` (required): exactly one of `java`, `python`, `dotnet`, `go`,
  `node`, `php`, or `ruby`.
- `from_version` (optional): baseline tag, for example `v41.0.0`; defaults to
  the latest released semantic-version tag in the selected library.
- `to_version` (optional): target tag, branch, or commit; defaults to `HEAD`.
- Require between one and three arguments. If the count is invalid or the
  language is unsupported, stop and show:
  `/release-notes-generation <language> [from_version] [to_version]`.

The canonical source repository is
`Adyen/adyen-<language>-api-library`. Do not accept a repository name, GitHub
identity, URL, or local checkout path in place of `language`.

## Preparation workflow

Complete every preparation step before delegation.

1. Resolve the output location:
  - Resolve the current working directory to an absolute `output_root`.
  - Require `output_root` to exist and be a directory.
  - The invocation directory does not need to be the selected API library's
    repository. In particular, this skill may run from
    `/Users/beppe/workspace/adyen-sdk-automation`.
  - Set the output paths to `<output_root>/RELEASE_NOTES.md` and
    `<output_root>/RELEASE_NOTES_VALIDATION.md`.
  - Require both paths to be direct children of `output_root` with exactly
    those filenames.

2. Normalize the requested range:
  - With only `language`, pass `from_ref: null` to request the latest released
    semantic-version tag and use `to_ref: HEAD`.
  - With one version argument, use it as `from_ref` and use `to_ref: HEAD`.
  - With two version arguments, use them as `from_ref` and `to_ref`.
  - Preserve supplied refs exactly for release-note text and the changelog URL.
  - Do not resolve refs locally. The droid resolves them after cloning the
    selected source repository.

3. Establish output authorization:
  - Check both output paths before delegation. If either exists, ask once for
    permission to overwrite the exact existing path or paths.
  - If permission is denied, stop without delegating or modifying either file.
  - Never treat invocation of this skill as implicit overwrite authorization.

4. Defensively recheck the prepared inputs:
  - Verify the validated language remains unchanged.
  - Verify `output_root` and both output paths remain valid.
  - Verify overwrite authorization still covers every existing output.
  - If any prepared value conflicts with current evidence, stop before
    delegation and report the conflict.

## Delegation workflow

After every preparation step succeeds:

1. Delegate exactly once to the `release-notes-generation-droid` droid.
2. Provide a self-contained handoff containing:
  - validated `language`
  - canonical GitHub `repository` identity in `<owner>/<repository>` form
  - absolute `output_root`
  - normalized `from_ref` and `to_ref`
  - absolute `release_notes_path` and `validation_path`
  - `overwrite_authorized: true` only when existing outputs were approved,
    otherwise `overwrite_authorized: false`
  - a statement that the droid must follow its full source acquisition,
    analysis, output, cleanup, and validation contract
3. Do not copy the droid's detailed analysis rules into the handoff.
4. Require a structured result containing `status` (`PASS` or `FAIL`), artifact
   paths, and either release-note contents or blocking reasons.
5. On `PASS`, verify that both expected files exist, the validation report
   contains every required literal heading and reports `PASS`, and the release
   notes end with the expected full changelog line.
6. On `FAIL`, verify that the validation report exists unless the droid
   explicitly reports that safe artifact writing was blocked before it could
   create one. Do not create, overwrite, or present `RELEASE_NOTES.md` as a
   successful output.
7. If the droid result or artifacts contradict the contract, report `FAIL`
   rather than repairing or guessing.

## Final result

On success:

- Report `PASS`.
- Provide the absolute paths to `RELEASE_NOTES.md` and
  `RELEASE_NOTES_VALIDATION.md`.
- Present the generated release notes.

On failure:

- Report `FAIL`.
- Provide the blocking reasons.
- Provide the absolute validation-report path when it was safely created.
- Never present `RELEASE_NOTES.md` as a successful output.
