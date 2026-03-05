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
