# Adyen SDK Automation

This is a set of Gradle build scripts to generate code for `Adyen/adyen-*-api-library` repositories. 

To generate all services (see [`adyen.sdk-automation-conventions.gradle`](/buildSrc/src/main/groovy/adyen.sdk-automation-conventions.gradle)) in all libraries:

> *Note:* The following models/services are not generated for Platform & Financial Services (legacy VIAS):
> * AccountAPI
> * FundAPI
> * Classic Platforms - Notifications

```
./gradlew services
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
```

### Development

Shared logic goes into `buildSrc`. Subprojects can extend and customize predefined tasks via extension
properties (`project.ext`) or reconfiguration (`tasks.named`).

For local testing of some library:

```shell
rm -rf go/repo && ln -s ~/workspace/adyen-go-api-library go/repo
```

To run unit tests:

```
./gradlew :buildSrc:test
```
