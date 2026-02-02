## Overview

This is the Adyen SDK Automation repository. It serves as a centralized set of tools to automatically generate and update code for all of Adyen's `adyen-*-api-library` repositories. The generation is based on Adyen's [OpenAPI specifications](https://github.com/Adyen/adyen-openapi).

This repository uses a combination of Gradle tasks and GitHub Actions to orchestrate the entire code generation and library update process.

## Code Generation Engine

The code generation process is powered by several key components:

- **[OpenAPI Generator](https://openapi-generator.tech/)**: We use the OpenAPI Generator CLI to transform the OpenAPI specifications into client-side code (models and services).
- **[Mustache Templates](https://mustache.github.io/)**: The generator uses custom Mustache templates to produce code that is tailored to the specific architecture and conventions of each Adyen library. These templates are typically stored within the individual library repositories (e.g., in a `/templates` folder).
- **Gradle**: Gradle is used to define and manage the automation tasks. It handles fetching the OpenAPI Generator, pulling the latest specifications, and running the generation commands for each target language. Shared logic is placed in the `buildSrc` directory.

## Automated Generation (CI/CD)

The primary code generation process is fully automated using GitHub Actions.

1.  **Trigger**: A workflow in this repository ([`.github/workflows/gradle.yml`](.github/workflows/gradle.yml)) is triggered by changes in the [adyen-openapi](https://github.com/Adyen/adyen-openapi) repository.
2.  **Execution**: The workflow executes the Gradle `services` task, which generates code for all services across all supported libraries (Java, .NET, Go, Node, PHP, Python, Ruby).
3.  **Pull Requests**: Once the code is generated, the workflow automatically creates Pull Requests in the respective API library repositories, which can then be reviewed and merged.

## Local Development Workflow

For developing new features, testing template changes, or debugging the generation process, you must run the generator from a local clone of this `adyen-sdk-automation` repository.

### 1. Set Up the Target Library

To generate code, the automation project needs access to the target Adyen API library. The simplest way to set this up is to use the `cloneRepo` Gradle task, which automatically clones the library's repository from GitHub into the corresponding `[language]/repo` directory.

- **For Java:**
  ```bash
  ./gradlew :java:cloneRepo
  ```
- **For Python:**
  ```bash
  ./gradlew :python:cloneRepo
  ```

This command works for all supported languages (`java`, `python`, `dotnet`, `go`, `node`, `php`, `ruby`) and will be skipped if the `repo` directory already exists.

**Note for active development:** If you already have a local clone of the library and wish to work on its code, you can manually create a symbolic link instead. First, remove the `[language]/repo` directory if it exists, and then run `ln -s /path/to/your/adyen-api-library [language]/repo`.

### 2. Run the Generator

You can now run the Gradle commands to generate code for the linked library. The commands follow a consistent structure.

- **To generate all services for a library (e.g., Java):**
  ```bash
  ./gradlew :java:services
  ```

- **To generate a single specific service (e.g., Checkout for PHP):**
  ```bash
  ./gradlew :php:checkout
  ```

- **To clean the repository before generating (recommended):**
  ```bash
  ./gradlew :go:cleanRepo :go:balancePlatform
  ```

- **For Node.js, you can specify the generator version via a CLI parameter:**
  ```bash
  ./gradlew :node:cleanRepo :node:checkout -PopenapiGeneratorVersion=5.4.0
  ```

Replace `java`, `php`, `go`, and `node` with the target language of your choice (`dotnet`, `python`, `ruby`).

## Language-Specific and Core Generation Logic

While the core generation is handled by OpenAPI Generator, each language requires specific logic to handle naming conventions, file placement, and library-specific conventions. This logic is defined within each language's `build.gradle` file.

The central, language-agnostic generation logic is defined in [`buildSrc/src/main/groovy/adyen.sdk-automation-conventions.gradle`](buildSrc/src/main/groovy/adyen.sdk-automation-conventions.gradle). This file contains the complete list of API services, defines the main Gradle generation tasks, and includes pre-processing steps to adapt the OpenAPI specifications for our needs.

For detailed implementation of language-specific logic, refer to the following files using Java as an example:

*   **Java**: The generation and post-processing steps (e.g., copying files, renaming webhook handlers) are defined in `java/build.gradle`. Webhook-specific generation is configured in `java/config.yaml`.

## Testing

To run the unit tests for the shared Gradle logic in `buildSrc`, execute:
```bash
./gradlew :buildSrc:test
```
