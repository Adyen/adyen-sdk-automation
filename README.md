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
