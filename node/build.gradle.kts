import com.adyen.sdk.Service
import com.adyen.sdk.SdkAutomationExtension
import org.openapitools.generator.gradle.plugin.tasks.GenerateTask

/**
 * This Gradle build script is designed to automate the generation of the TypeScript code from the OpenAPI specifications.
 * It orchestrates the entire process, from code generation to copying the generated files in the correct source directories
 * (services, typings).
 * It includes verification steps to confirm the outcome of the generation.
 */
plugins {
    id("adyen.sdk-automation-conventions")
}

val sdkAutomation = extensions.getByType<SdkAutomationExtension>()
sdkAutomation.generator.set("typescript")

val services = sdkAutomation.services.get()
val serviceNaming = sdkAutomation.serviceNamingCamel.get()

services.forEach { svc ->
    // service name starting lowercase
    val serviceName = serviceNaming[svc.id]!!
    // service unmodified (starting with uppercase)
    val originalServiceName = svc.name

    // Generation
    tasks.named<GenerateTask>("generate${svc.name}") {
        templateDir.set("$projectDir/repo/templates-v7/typescript")

        apiNameSuffix.set("Api")
        additionalProperties.putAll(mapOf(
            "modelPropertyNaming" to "original",
            "serviceName" to serviceName,
            "originalServiceName" to originalServiceName,
            "enumPropertyNaming" to "PascalCase"
        ))

        // for webhooks apply extra config.yaml (to generate WebhookHandler)
        if (svc.id.endsWith("webhooks")) {
            configFile.set("$projectDir/config.yaml")
        }
    }

    /**
     * Copy models task
     * - copy generated models from build (generated code) to the library `/src/typings` folder
     * - rename to start with lowercase (to follow naming conventions)
     * - rename specific files:
     *      - all.ts must be renamed to models.ts
     *      - webhookHandler.ts must be renamed to specific handler (i.e. reportWebhooksHandler.ts)
     */
    val deployModels = tasks.register<Sync>("deploy${svc.name}Models") {
        group = "deploy"
        description = "Deploy ${svc.name} models into the repo."
        dependsOn("generate${svc.name}")
        outputs.upToDateWhen { false }

        from(layout.buildDirectory.dir("services/${svc.id}/models")) {
            eachFile {
                val name = this.name
                if (name.isNotEmpty()) {
                    // copy and rename to start with lowercase
                    this.name = name[0].lowercase() + name.substring(1)
                }
            }

            // Rename specific files
            rename { fileName ->
                when (fileName) {
                    "all.ts" -> "models.ts"
                    "webhookHandler.ts" -> {
                        val handlerName = "${svc.name}Handler.ts"
                        handlerName[0].lowercase() + handlerName.substring(1)
                    }
                    else -> fileName
                }
            }

            includeEmptyDirs = false
        }
        into(layout.projectDirectory.dir("repo/src/typings/$serviceName"))
    }

    /**
     * Copy services task
     * - copy generated models from build (generated code) to the library services folder
     * - rename to start with lowercase (to follow naming conventions)
     *
     * Note: webhook specs (i.e. ConfigurationWebhooks, etc.. ) are skipped because Webhooks generation must only creates models
    */
    val deployServices = tasks.register<Sync>("deploy${svc.name}Services") {
        group = "deploy"
        description = "Deploy ${svc.name} into the repo."
        dependsOn("generate${svc.name}")
        outputs.upToDateWhen { false }
        onlyIf { !svc.isWebhook } // skip webhooks (this task is for generating service classes only)

        from(layout.buildDirectory.dir("services/${svc.id}/apis")) {
            include("*Api.ts")
            eachFile {
                val name = this.name
                if (name.isNotEmpty()) {
                    // copy and rename to start with lowercase
                    this.name = name[0].lowercase() + name.substring(1)
                }
            }
            includeEmptyDirs = false
        }
        into(layout.projectDirectory.dir("repo/src/services/$serviceName"))
        // copy index.ts (export service classes)
        from(layout.buildDirectory.dir("services/${svc.id}")) {
            include("index.ts")
        }
    }

    tasks.named(svc.id) {
        dependsOn(deployModels, deployServices)
    }
}

// Test binlookup
tasks.named("binlookup") {
    doLast {
        assert(file("${layout.projectDirectory}/repo/src/typings/binLookup/amount.ts").exists())
        assert(file("${layout.projectDirectory}/repo/src/services/binLookupApi.ts").exists())
    }
}
// Test checkout
tasks.named("checkout") {
    doLast {
        assert(file("${layout.projectDirectory}/repo/src/typings/checkout/models.ts").exists())
        assert(file("${layout.projectDirectory}/repo/src/typings/checkout/objectSerializer.ts").exists())
        assert(file("${layout.projectDirectory}/repo/src/typings/checkout/amount.ts").exists())
        assert(file("${layout.projectDirectory}/repo/src/services/checkout/paymentsApi.ts").exists())
        assert(file("${layout.projectDirectory}/repo/src/services/checkout/index.ts").exists())
    }
}
// Test balanceplatform
tasks.named("balanceplatform") {
    doLast {
        assert(file("${layout.projectDirectory}/repo/src/typings/balancePlatform/models.ts").exists())
        assert(file("${layout.projectDirectory}/repo/src/typings/balancePlatform/objectSerializer.ts").exists())
        assert(file("${layout.projectDirectory}/repo/src/typings/balancePlatform/amount.ts").exists())
        assert(file("${layout.projectDirectory}/repo/src/services/balancePlatform/accountHoldersApi.ts").exists())
        assert(file("${layout.projectDirectory}/repo/src/services/balancePlatform/index.ts").exists())
    }
}
// Test acswebhooks
tasks.named("acswebhooks") {
    doLast {
        assert(file("${layout.projectDirectory}/repo/src/typings/acsWebhooks/amount.ts").exists())
        // verify Webhook Handler is created
        assert(file("${layout.projectDirectory}/repo/src/typings/acsWebhooks/acsWebhooksHandler.ts").exists())
        // verify objectSerializer is created
        assert(file("${layout.projectDirectory}/repo/src/typings/acsWebhooks/objectSerializer.ts").exists())
        // verify no service package is created for a webhook (Webhooks generation must only creates models)
        assert(!file("${layout.projectDirectory}/repo/src/services/acsWebhooks").exists())
        // verify no API class is created for a webhook (Webhooks generation must only creates models)
        assert(!file("${layout.projectDirectory}/repo/src/services/acsWebhooksApi.ts").exists())
    }
}

tasks.named("capital") {
    doLast {
        assert(file("${layout.projectDirectory}/repo/src/typings/capital/amount.ts").exists())
        assert(file("${layout.projectDirectory}/repo/src/services/capital/grantsApi.ts").exists())
        assert(file("${layout.projectDirectory}/repo/src/services/capital/grantOffersApi.ts").exists())
        assert(file("${layout.projectDirectory}/repo/src/services/capital/grantAccountsApi.ts").exists())
    }
}
