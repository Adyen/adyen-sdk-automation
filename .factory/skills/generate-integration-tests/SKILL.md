---
name: generate-integration-tests
description: >-
  Generate real Adyen TEST-environment integration tests in a local Java,
  Node.js, or Ruby API library from every Gherkin scenario under
  integration-test-generator/test-scenarios. Use when a user asks to create or
  refresh SDK integration tests from the shared scenarios.
user-invocable: true
version: 1.0.0
---

# Generate API library integration tests

Generate integration tests from the language-agnostic scenarios while treating
the selected API library as the source of truth for test structure, naming,
public API usage, and validation.

## Non-negotiable constraints

- Process every `.feature` file under
  `integration-test-generator/test-scenarios`; do not offer or apply a subset
  filter.
- Supported libraries are exactly `java`, `node`, and `ruby`.
- Edit test case source files only. Do not edit production code, generated SDK
  code, helpers, fixtures, runner configuration, build files, package scripts,
  environment examples, or documentation in the target library.
- Generate real API integration tests. Do not use mocks, stubs, recorded
  responses, WebMock, Nock, or fake clients.
- Always target the Adyen TEST environment, never LIVE.
- Never put credentials, tokens, or real resource identifiers in source files,
  logs, commands, or responses.
- Never execute the generated integration tests or any command that can
  discover and run them.
- Treat all existing target-library changes as user work. Never overwrite,
  reformat, move, delete, clean, restore, or revert them.
- Complete preflight for all scenarios before editing any target file. If one
  scenario is blocked, make no edits.

## 1. Select the library

Always use `AskUser` to ask which library to generate tests for, with these
single-choice options:

- Java
- Node.js
- Ruby

Normalize the answer to `java`, `node`, or `ruby`. Reject every other value.

## 2. Locate and verify the repositories

1. Resolve the current automation repository root with Git.
2. Let `workspace` be its parent directory.
3. Resolve the target as the exact sibling
   `<workspace>/adyen-<language>-api-library`.
4. Stop if that exact directory does not exist. Do not clone a repository, use
   `<language>/repo`, search other paths, or accept a replacement path.
5. Verify the target is a Git worktree whose canonical root is that exact
   directory and whose root directory has the expected name.

## 3. Read the sources of truth

Before planning tests:

1. Read the automation repository's `AGENTS.md`.
2. Read `integration-test-generator/test-scenarios/README.md` and every
   `.feature` file below `integration-test-generator/test-scenarios`.
3. Read the target repository's root `AGENTS.md` and every more-specific
   instruction file that applies to likely test destinations.
4. Inspect the target's current Git status and record all modified and
   untracked paths.
5. Inspect the target's existing real integration tests, adjacent test files,
   test utilities, runner configuration, dependency/build configuration, and
   public SDK service and model APIs. Read configuration only for context; it
   is outside the allowed edit scope.

Do not infer conventions from another language library. The selected target
repository is authoritative.

## 4. Preflight every scenario

Build a coverage ledger before writing. For each feature and scenario, resolve:

- the destination test file and locally conventional suite/test name;
- the exact Gherkin scenario title for the required test header comment;
- background setup and the existing TEST-environment client mechanism;
- every runtime value introduced by a `Given` step;
- the public service/API class and operation method;
- request construction using native public types or hashes, as appropriate;
- path or query arguments and their order;
- success response type and narrow assertions;
- the library's concrete API exception type, status access, and error-body
  handling for failure scenarios;
- resource creation dependencies required to invoke the endpoint.

Preserve scenario intent exactly. Convert JSON doc strings to the target
language without changing field names or values, except `${name}`
interpolation. Generate unique values using the target's existing convention
and applicable API length limits.

Use only public SDK entry points and imports. Follow local formatting, naming,
test framework, environment access, error assertions, file placement, and
resource lifecycle patterns exactly.

Preflight is blocked when any of the following is true:

- an operation, request type, exception, assertion, or destination is
  ambiguous;
- required integration-test infrastructure is absent;
- implementation would require editing anything other than test case source;
- a required credential or resource cannot be obtained through an existing
  target-library mechanism from runtime environment variables;
- a planned destination is already modified or is an untracked user file;
- scenarios conflict with target-library instructions.

If blocked, stop before editing and report a concise list keyed by feature and
scenario. Do not invent APIs, conventions, infrastructure, or setup.

## 5. Generate the tests

Only after every ledger entry is complete:

1. Create or update the planned test case files.
2. Immediately above each generated test case, add a language-appropriate
   comment header in this exact form, preserving the Gherkin title:

   ```text
   Scenario: <exact scenario title>
   ```

3. Keep arrange, act, and assert structure consistent with nearby tests.
4. Reuse existing client/environment utilities without modifying them.
5. Keep assertions limited to those expressed by the scenario.
6. Catch and inspect errors using the target library's concrete exception
   patterns; do not accept a test merely because any exception was thrown.
7. Apart from the required scenario header, do not add comments that duplicate
   the code or mention the generator.

## 6. Review and validate without live calls

Review the target-library diff and verify:

- every feature and scenario has exactly one corresponding test;
- every generated test has a comment header containing its exact Gherkin
  scenario title;
- only planned test case source files changed;
- no baseline user changes were altered;
- no mock/stub framework was introduced;
- all clients select TEST;
- no secret or real identifier was added;
- request fields, operations, dynamic values, and assertions match the
  scenarios;
- imports and APIs are public and consistent with nearby tests.

Before any validation command, verify the language runtime and required build
tool are installed, as required by the target repository instructions. Run
only the narrowest checks guaranteed not to execute or discover integration
tests, for example a syntax check, test compilation with execution disabled,
or lint scoped to changed files. Avoid broad auto-fix or formatting commands.

If no safe non-live check exists, skip command validation and say why. Never
run the integration-test command, a default test command that includes the
generated files, or any test against Adyen.

## 7. Report

Report:

- selected library and verified target path;
- generated or updated test files;
- scenario coverage count;
- non-live checks run and their results;
- live integration tests skipped by policy;
- any validation that could not be performed.
