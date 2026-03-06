import com.adyen.sdk.Service
import com.adyen.sdk.SdkAutomationExtension
import org.openapitools.generator.gradle.plugin.tasks.GenerateTask

plugins {
    id("adyen.sdk-automation-conventions")
}

val sdkAutomation = extensions.getByType<SdkAutomationExtension>()
sdkAutomation.generator.set("go")
sdkAutomation.templates.set("templates/custom")
// configFile is not in extension but we can use extra or just hardcode if it's fixed
project.extra["configFile"] = "templates/config.yaml"
sdkAutomation.removeTags.set(false)

val services = sdkAutomation.services.get()

// Service renaming
tasks.named<GenerateTask>("generateLegalEntityManagement") {
    sdkAutomation.serviceName.set("LegalEntity")
    additionalProperties.set(mapOf(
        "serviceName" to "LegalEntity"
    ))
}
tasks.named<GenerateTask>("generatePayout") {
    additionalProperties.set(mapOf(
        "serviceName" to ""
    ))
}
tasks.named<GenerateTask>("generatePayment") {
    additionalProperties.set(mapOf(
        "serviceName" to ""
    ))
}

tasks.withType(GenerateTask::class).configureEach {
    enablePostProcessFile.set(true)
    globalProperties.set(mapOf(
        "apis" to "",
        "models" to "",
        "supportingFiles" to "client.go",
        "apiTests" to "false",
        "apiDocs" to "false",
        "modelDocs" to "false"
    ))
}

// Deployment
services.forEach { svc ->
    val generateTask = "generate${svc.name}"
    val deploy = tasks.register<Copy>("deploy${svc.name}") {
        group = "deploy"
        description = "Copy ${svc.name} files into the repo."
        dependsOn(generateTask)
        outputs.upToDateWhen { false }

        // delete existing services and models
        doFirst {
            delete(layout.projectDirectory.dir("repo/src/${svc.id}"))
        }

        from(layout.buildDirectory.dir("services/${svc.id}"))
        include("**/*")
        into(layout.projectDirectory.dir("repo/src/${svc.id}"))
    }

    tasks.named(svc.id) {
        dependsOn(deploy)
    }

    tasks.named<GenerateTask>(generateTask) {
        packageName.set(svc.id)
    }
}

tasks.named<GenerateTask>("generatePayment") {
    packageName.set("payments")
}

tasks.named<GenerateTask>("generateLegalEntityManagement") {
    packageName.set("legalentity")
}

// Generate and rename webhooks
services.filter { it.name.endsWith("Webhooks") }.forEach { svc ->
    val singular = svc.id.removeSuffix("s") // drop s (e.g. from AcsWebhooks to AcsWebhook)
    tasks.named<GenerateTask>("generate${svc.name}") {
        packageName.set(singular)
    }
    tasks.named<Copy>("deploy${svc.name}") {
        val targetDir = layout.projectDirectory.dir("repo/src/$singular")
        // Drop content first (except webhook_handler.go)
        doFirst {
            targetDir.asFile.listFiles()?.forEach { file ->
                if (file.name != "webhook_handler.go") {
                    file.delete()
                }
            }
        }
        into(targetDir) // Copy models
    }
}

tasks.named<Copy>("deployLegalEntityManagement") {
    into(layout.projectDirectory.dir("repo/src/legalentity"))
}

tasks.named<Copy>("deployPayment") {
    into(layout.projectDirectory.dir("repo/src/payments"))
}

// Small services (skip client.go as single class service does not need an "index" to group multiple tags)
services.filter { it.small }.forEach { svc ->
    tasks.named<Copy>("deploy${svc.name}") {
        exclude("client.go")
    }
}

// Webhooks (skip client.go and copy models only)
services.filter { it.name.endsWith("Webhooks") }.forEach { svc ->
    tasks.named<Copy>("deploy${svc.name}") {
        exclude("client.go")
    }
}

// Services with a RestServiceError model
listOf("generateBalancePlatform", "generateTransfers", "generateManagement").forEach {
    tasks.named<GenerateTask>(it) {
        additionalProperties.put("hasRestServiceError", "true")
    }
}

// Test small services
tasks.named("binlookup") {
    doLast {
        assert(file("${layout.projectDirectory}/repo/src/binlookup/model_amount.go").exists())
        assert(!file("${layout.projectDirectory}/repo/src/binlookup/api_default.go").exists())
        assert(file("${layout.projectDirectory}/repo/src/binlookup/api_general.go").exists())
    }
}
// Test services
tasks.named("checkout") {
    doLast {
        assert(file("${layout.projectDirectory}/repo/src/checkout/model_amount.go").exists())
        assert(!file("${layout.projectDirectory}/repo/src/checkout/api_default.go").exists())
        assert(file("${layout.projectDirectory}/repo/src/checkout/api_donations.go").exists())
    }
}
// Test webhooks
tasks.named("acswebhooks") {
    doLast {
        assert(file("${layout.projectDirectory}/repo/src/acswebhook/model_amount.go").exists())
        // Note: original check was against checkout/api_default.go which seems wrong but I'll keep it as is if it was in the original
        assert(!file("${layout.projectDirectory}/repo/src/checkout/api_default.go").exists())
    }
}
