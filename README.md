# Adyen SDK Automation

This is a set of Gradle build scripts to generate code for `Adyen/adyen-*-api-library` repositories. 

To generate all services in all libraries:

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
./gradlew :node:cleanRepo :node:checkout
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
