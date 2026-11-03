[![Update SDKs](https://github.com/Adyen/adyen-sdk-automation/actions/workflows/gradle.yml/badge.svg)](https://github.com/Adyen/adyen-sdk-automation/actions/workflows/gradle.yml)

# Adyen SDK Automation

This is a set of Gradle build scripts to generate code for `Adyen/adyen-*-api-library` repositories. 

This project uses **Gradle Kotlin DSL**.

To generate all services in all libraries, run:

```
./gradlew services
```
*Note:*  Ensure that the service is in the following list: [`adyen.sdk-automation-conventions.gradle.kts`](/buildSrc/src/main/kotlin/adyen.sdk-automation-conventions.gradle.kts).

For all services in a library, run:

```
./gradlew :go:services
```

For a single specific service:

```
./gradlew php:checkout
```

To clean up spec patches:

```
./gradlew cleanSpecs
```

To clean up all the generated artifacts and repository modifications:

```
./gradlew cleanRepo
```

Typical usage during development:

```
./gradlew :dotnet:cleanRepo :dotnet:checkout
```

For Node.js, set the generator version via CLI:

```
./gradlew :node:cleanRepo :node:checkout -PopenapiGeneratorVersion=5.4.0
./gradlew :java:cleanRepo :java:checkout -PopenapiGeneratorVersion=7.11.0
./gradlew :dotnet:cleanRepo :dotnet:checkout -PopenapiGeneratorVersion=7.11.0
```

### Development

Shared logic goes into `buildSrc`. Subprojects can extend and customize predefined tasks via the type-safe `SdkAutomationExtension` or reconfiguration (`tasks.named`).

To access the configuration in a subproject:

```kotlin
val sdkAutomation = extensions.getByType<SdkAutomationExtension>()
// access properties
val services = sdkAutomation.services.get()
```

For local testing of some library:

```shell
rm -rf go/repo && ln -s ~/workspace/adyen-go-api-library go/repo
rm -rf java/repo && ln -s ~/workspace/adyen-java-api-library java/repo
rm -rf dotnet/repo && ln -s ~/workspace/adyen-dotnet-api-library dotnet/repo
```

To run unit tests:

```
./gradlew :buildSrc:test
```

### Automated PR Reviewers

The `Update SDKs` workflow requests one reviewer only when it creates a new SDK pull request. Updates to existing pull requests leave their reviewers untouched. Configure the reviewer pool with an `SDK_REVIEWERS` repository variable containing a comma-separated list of GitHub usernames:

```
alice,bob-smith,carol
```

The workflow converts the full `adyen-openapi` commit SHA to an integer and uses its modulo against the pool size. This makes the selection deterministic for retries of the same commit and distributes reviews across the pool, but does not guarantee that consecutive commits select different reviewers.

Every reviewer must have access to all target SDK repositories. The `ADYEN_AUTOMATION_BOT_ACCESS_TOKEN` must also have permission to request reviews. The workflow fails before creating a pull request when the reviewer pool is missing or invalid.

### Checking SDK coverage

There are two checks: a quick check of the service list and a detailed check that
generates SDK code.

#### Check the service list

This compares the published OpenAPI specs with `config/services.json`. It shows
APIs missing from the list, newer API versions, and missing spec files.

```shell
./gradlew specs
python3 .github/scripts/check_spec_coverage.py
```

These findings are warnings, so they do not fail the check. Invalid configuration
or specs that cannot be read do fail it.

`config/spec-coverage-baseline.json` records known gaps and their reasons.
`UNREVIEWED` means the reason still needs review. When you add a missing service
or update an older version, remove the matching baseline entry.

When looking for the latest public version, the check skips specs marked
`info.x-publicVersion: false`. It still checks that every spec file named in the
service list exists.

The **Spec Coverage** GitHub Action runs every weekday at **07:30 UTC**, on pull
requests that change its watched files, or when started manually. Results appear
in the run summary. It does not change files or open pull requests.

#### Generate a detailed SDK report

This check creates temporary SDK clones, generates code, and compares the result
with the code already in each SDK. Your existing SDK checkouts are not changed.

In GitHub, the **SDK Coverage** workflow runs every weekday at **07:30 UTC** and
on pull requests to `main` that change the coverage checks, service catalog,
baseline, or generation inputs. Scheduled runs check all services across all
seven SDKs and start once the workflow is merged into the default branch.
Open its completed run to see the per-language table in the **Summary**, or
download the **sdk-coverage** artifact for the Markdown report and generation log.
The report is still published when a service check fails, if one was produced.

Once the workflow is on the default branch, you can also open **Actions → SDK
Coverage → Run workflow**, select a branch, and optionally enter comma-separated
services such as `checkout,management`. Leave the field empty to check all
services across all seven SDKs. This workflow does not change SDK repositories or
open pull requests.

For example, to check Checkout and Management:

```shell
python3 .github/scripts/sdk_coverage.py --services checkout,management --jobs 2 --output /tmp/sdk-coverage.md
```

- Leave out `--services` to check all services in `config/services.json`.
- `--jobs 2` checks up to two SDKs at the same time.
- `--output` chooses where to save the report. Without it, the report is saved as
  `sdk-coverage.md` in this repository. Git ignores that file.

Generation uses the committed automation code and service list on your current
branch. Uncommitted changes to those inputs are not included.

You need the SDK build tools and formatters installed locally. The script may
also install formatter dependencies inside its temporary clones.

Differences between generated and existing code are warnings. Missing spec files
are skipped and shown as `Missing spec`. Setup, generation, formatting, or
inspection failures fail the run after the report is saved.

Python and Ruby webhook generation is not supported. For unsupported services,
the report separately checks committed SDK source. When matching source is found,
it adds `in SDK` and a version when known. Otherwise, the label stays `Unsupported`;
this does not mean the service is absent. Unclear evidence or inspection failures
are labelled `presence not assessed`. The log includes matching files and the SDK
commit. Generic webhook or HMAC helpers do not count as evidence for a specific
webhook family. Finding source does not prove complete webhook support.

If a generation check cannot confirm that a service is up to date, the report
shows `Not assessed` rather than `Current`.

### Generating Release Notes

A Factory skill and droid are included to generate evidence-backed release notes for an Adyen API library. The skill validates the request and manages the output files, while the droid clones the selected library into a temporary directory, analyzes the release range, validates the result, and cleans up the clone.

The workflow is defined in:

- [`.factory/skills/release-notes-generation/SKILL.md`](.factory/skills/release-notes-generation/SKILL.md)
- [`.factory/droids/release-notes-generation-droid.md`](.factory/droids/release-notes-generation-droid.md)

Run the skill from the directory where the output files should be created:

```
/release-notes-generation <language> [from_version] [to_version]
```

For example:

```
/release-notes-generation java v41.0.0 HEAD
/release-notes-generation python
```

Supported languages are `java`, `python`, `dotnet`, `go`, `node`, `php`, and `ruby`.

When `from_version` is omitted, the latest released semantic-version tag is used. When `to_version` is omitted, it defaults to `HEAD`. No local SDK checkout is required.

The workflow writes two files to the invocation directory:

- `RELEASE_NOTES.md`, the publishable release notes
- `RELEASE_NOTES_VALIDATION.md`, an auditable validation report. It can be deleted after the Release Notes are generated.

Existing output files are only overwritten after confirmation. Release notes are produced only when validation passes; on failure, the validation report records the blocking reasons.
