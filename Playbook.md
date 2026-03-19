# SDK Automation Engineering Playbook

**Welcome to the Adyen SDK Automation Team.**

This playbook is your definitive guide to understanding, operating, and improving the engine that powers Adyen's client libraries. Whether you are fixing a bug in the Java SDK or adding support for a brand new API, this document covers the *Why*, *What*, and *How*.

---

## 🏗️ 1. The Big Picture

### The Problem
Adyen has many APIs (Checkout, Payments, Platforms, etc.) and supports many languages (Java, .NET, Go, Node.js, PHP, Python, Ruby). Manually writing and maintaining SDKs for every combination would be slow, error-prone, and impossible to scale.

### The Solution: `adyen-sdk-automation`
We built a centralized **Code Generation Factory**.
1.  **Input:** OpenAPI Specs (The single source of truth for our API definitions).
2.  **Process:** An automated pipeline (Gradle + OpenAPI Generator).
3.  **Output:** Production-ready SDK code pushed directly to our GitHub repositories.

### Key Concepts

| Term | Definition |
| :--- | :--- |
| **OpenAPI (OAS)** | A standard JSON/YAML file describing an API (endpoints, request bodies, responses). |
| **SDK (Client Library)** | The code wrappers (e.g., `checkout.payments()`) we give to merchants so they don't have to write raw HTTP requests. |
| **Generator** | The software that reads an OpenAPI spec and outputs code. |
| **Mustache** | The template language used to define *how* the code should look (e.g., `public class {{classname}}`). |
| **Gradle** | The build tool that orchestrates the entire process (downloading specs, running the generator, moving files). Uses **Kotlin DSL** (`.gradle.kts`). |

---

## 🏭 2. Architecture: Inside the Factory

The repository is structured as a **Gradle Multi-Project Build**.

### The "Brain": `buildSrc/`
This is where the custom logic lives. It controls the entire factory.
*   **`src/main/kotlin/com/adyen/sdk/SdkAutomationExtension.kt`**: **The Configuration Model.**
    *   Defines the type-safe structure for project settings (generator, services, naming).
*   **`src/main/kotlin/adyen.sdk-automation-conventions.gradle.kts`**: **The Master Schedule.**
    *   Defines every API we support (the `Service` list).
    *   Dynamically creates tasks for every service (e.g., `generateCheckout`).
    *   Pre-processes specs (renaming tags, adding extensions) before generation.

### The "Assembly Lines": Language Subprojects
Each language (`java/`, `python/`, `dotnet/`, etc.) is a separate subproject.
*   **`build.gradle.kts`**: Configures the generator for that language (naming conventions, library choices).
*   **`repo/`**: A **phantom directory**. When you run setup, the *actual* target SDK repository (e.g., `adyen-java-api-library`) is cloned here.
*   **Deployment Tasks**: Scripts that copy generated code from the temporary build folder into the `repo/` folder, often performing cleanup or renaming along the way.

---

## 🚀 3. Getting Started: Your First Run

### Prerequisites
*   **Java JDK 17+** (The project uses Gradle 9)
*   **Git**

### Step 1: Clone & Setup
Clone this repository. Then, prepare the target language environment. You cannot generate code into thin air; you need the destination repository.

```bash
# Example: Setup for Java
./gradlew :java:cloneRepo
```
*What this does:* It clones the official `adyen-java-api-library` into `java/repo`.  
*⚡ Pro tip*: Clone instead the library in its own folder and use symlink, see [Pro-Tips & Troubleshooting](#-pro-tips--troubleshooting)

### Step 2: Generate Code
Run the generator for a specific service (e.g., Checkout).

```bash
./gradlew :java:checkout
```
*What this does:*
1.  **Downloads** the OpenAPI specs (if the folder `schema` doesn't exist).
2.  **Runs** the generator using the templates in `java/repo/templates`.
3.  **Outputs** the generated code in the `build` folder.
4.  **Adjusts** and **copies** the code into `java/repo/...`.  

*⚡ Pro tip*: Generate all services with `/gradlew :java:services`  
*⚡ Pro tip*: Delete regularly the `schema` folder to clone again the OpenApi specs (make sure you are using the latest version)

### Step 3: Verify
Navigate to `java/repo` and check the status. Open the library in a different window if you have created a symlink.
```bash
cd java/repo
git status
```
You should see the newly generated files.

---

## 🛠️ 4. Engineer's Workflow: The "How-To"

There are typically 4 worklows:
- Fix the code generation
- Add a new endpoint, attribute or enum
- Update an existing API or Webhook
- Add a new API or Webhook

### Scenario A: Working on a new feature or bug fix
*The Goal: The generated code has a syntax error or doesn't follow our style guide.*

In this scenario you **work locally** to modify and test the changes.

1.  **Locate the Template:** **NEVER** edit the generated `.java` file directly. It will be overwritten.
    *   Go to `[language]/repo/templates`.
    *   Find the relevant file (e.g., `api.mustache` for endpoints, `pojo.mustache` for models).
2.  **Edit the Template:** Fix the logic (e.g., add a missing semicolon, change a variable name).
3.  **Re-run Generation:**
    ```bash
    ./gradlew :java:checkout
    ```
4.  **Verify:** Check if the output code is now correct.
5.  **Add Tests:** When applicable, add new tests in the SDK Automation Bot and/or the library source code
6.  **Commit:** You commit the changes *in the target SDK repository* (`java/repo`), not here.


### Scenario B: Adyen Releases a New API Feature
*The Goal: Update the SDKs to reflect a change in the API (e.g., a new field).*

In this scenario the public [OpenAPI specs](https://github.com/Adyen/adyen-openapi/tree/main) have been updated and
the SDK Automation Bot has generated a PR-per-service (i.e. Checkout) in each library repository.

1.  **Review PRs:** Review the PRs in the library repository.
2. **Add Tests:** When applicable, checkout the branch locally (or use Codespaces) and add new unit tests.
   a. Is there a new endpoint or new webhook event? **MUST add** new unit tests.
   a. Is there a new attribute or enum value? **MAY add** new unit tests.
3.  **Label:** Add the correct label in the PR (Improvement, Breaking Change)
4.  **Merge:** Approve and merge the PR

### Scenario C: Upgrading an existing API
*The Goal: Update the SDKs to upgrade an existing API version.*

In this scenario there is a new version of an API and the SDK Automation Bot must be updated.

1.  **Update the Service:**
    *   Open `buildSrc/src/main/kotlin/adyen.sdk-automation-conventions.gradle.kts`.
    *   Update the API version in the `servicesList` list: `Service(name = "NewApiVersion", version = 2")`.
2.  **Run:** `./gradlew :java:newApiVersion`.
3.  **Verify:** Confirm the new service is updated.
4.  **Add Tests:** When applicable, checkout the branch locally (or use Codespaces) and add new unit tests the library source code.
5.  **README.MD:** Edit `README.MD` file to update the versiong of the API/Webhook.
6.  **Commit:** You commit the changes in `adyen-sdk-automation` and in the target SDK repository* (`java/repo`) (*).

(*) Alternatively, commit and push the changes in `adyen-sdk-automation` only, then review the new PRs.

### Scenario D: Adding a Brand New Service
*The Goal: Update the SDKs to support a new Adyen Product.*

1.  **Register the Service:**
    *   Open `buildSrc/src/main/kotlin/adyen.sdk-automation-conventions.gradle.kts`.
    *   Add to the `servicesList` list: `Service(name = "NewProduct", version = 1")`.
2.  **Configure Deployment (Language Dependent):**
    *   In `java/build.gradle.kts` (or other languages), ensure there is logic to copy files for this new service.
3.  **Run:** `./gradlew :java:newProduct`.
4.  **Verify:** Confirm the new service is generated.
5.  **Add Tests:** Add new unit tests the library source code
6.   **README.MD:** Edit `README.MD` file to include the new API/Webhook version
7.  **Commit:** You commit the changes in `adyen-sdk-automation` and in the target SDK repository* (`java/repo`) (*).

(*) Alternatively, commit and push the changes in `adyen-sdk-automation` only, then review the new PR and add the unit
testing.


---

## 🎣 6. Special Component: Webhooks

Webhooks are different. Unlike standard APIs where we generate a *Client* to make requests, for Webhooks we generate a *Handler* to receive and deserialize events.

### The Mechanism
1.  **Detection:** The `adyen.sdk-automation-conventions.gradle.kts` file injects a special extension `x-webhook-root: true` into the OpenAPI spec for the root model of the webhook (e.g., `BalancePlatformNotificationResponse`).
2.  **Configuration (`config.yaml`):**
    *   Inside each language folder (e.g., `java/config.yaml`), we define specific rules for webhooks.
    *   This file tells the generator to use a specific supporting file (e.g., `webhook_handler.mustache`) instead of just standard models.
    *   *Example Content:*
        ```yaml
        files:
          webhook_handler.mustache:
            folder: src/main/java/com/adyen/model
            destinationFilename: WebhookHandler.java
            templateType: SupportingFiles
        ```
3.  **Generation:**
    *   The generator creates a generic `WebhookHandler.java` (or equivalent).
4.  **Deployment (Renaming):**
    *   The `deploy...Handlers` task in `build.gradle.kts` moves this file and renames it to match the service (e.g., `ConfigurationWebhooksHandler.java`).
    *   This allows us to have distinct handlers for different webhook types (Management, Platforms, etc.) even though they start from the same generic template.

### How to debug Webhooks
*   **Missing Handler?** Check `config.yaml` to ensure the template is mapped.
*   **Wrong Class Name?** Check the `deploy...Handlers` task in `build.gradle.kts` to see how the file is being renamed and moved.

---

## 📚 7. External Technology Reference

Master these tools to master this repo.

### The Standards
*   **[OpenAPI Specification](https://swagger.io/specification/):** Understand the input format (JSON/YAML).
*   **[Mustache Manual](https://mustache.github.io/mustache.5.html):** Learn the template syntax (`{{#section}}`, `{{value}}`).

### The Tools
*   **[OpenAPI Generator Docs](https://openapi-generator.tech/):** The core engine references.
*   **[Gradle Training](https://gradle.org/training/):** Learn how build scripts work.
*   **[GitHub Actions](https://docs.github.com/en/actions):** Understand the `.github/workflows` that run this automation in the cloud.

### Adyen Context
*   **[Adyen API Explorer](https://docs.adyen.com/api-explorer/):** The visual representation of the APIs we automate.
*   **[Adyen OpenAPI Repo](https://github.com/Adyen/adyen-openapi):** The source of our specs.

---

## ⚡ Pro-Tips & Troubleshooting

*   **Symlinks are your friend:** If you already have the `adyen-java-api-library` cloned elsewhere on your machine, don't use `cloneRepo`. instead, symlink it:
    `ln -s ~/workspace/adyen-java-api-library java/repo`
*   **Debug Mode:** Use `./gradlew ... --info` to see exactly what the generator is doing.
*   **Cleanliness:** If things act weird, run a clean:
    `./gradlew :java:cleanRepo`
*   **Webhooks are Special:** They often require custom "Handler" logic. Check `config.yaml` in the language folders for special configuration rules.
*   **Delete regularly** the `schema` folder to clone again the OpenAPI specs
*   **Pre-process**: OpenAPI schema (in the `schema` folder) are manipulated before kicking off the generation:
    - `x-webhook-root` extension is added to mark Webhook events
    - tags named `General` are renamed to match the name of the API
    - endpoint `operationId` is overriden with `x-methodName` (extension used to name the generated methods/functions in the SDKs)