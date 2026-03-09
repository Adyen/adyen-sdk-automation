import com.adyen.sdk.Service
import com.adyen.sdk.SdkAutomationExtension
import org.openapitools.generator.gradle.plugin.tasks.GenerateTask

plugins {
    id("adyen.sdk-automation-conventions")
}

val sdkAutomation = extensions.getByType<SdkAutomationExtension>()
sdkAutomation.generator.set("python")

val services = sdkAutomation.services.get()
services.find { it.id == "payment" }?.small = false

// Service renaming
val serviceNaming = sdkAutomation.serviceNamingCamel.get().toMutableMap()
serviceNaming.putAll(mapOf(
    "binlookup" to "binlookup",
    "payment" to "payments",
    "posterminalmanagement" to "terminal",
    "payout" to "payouts"
))

services.forEach { svc ->
    val serviceName = serviceNaming[svc.id]!!

    // Generation
    tasks.named<GenerateTask>("generate${svc.name}") {
        engine.set("mustache")
        configFile.set("$projectDir/config.yaml")
        additionalProperties.putAll(mapOf(
            "serviceName" to serviceName
        ))
    }

    // Deployment
    val deployServices = tasks.register<Sync>("deploy${svc.name}Services") {
        group = "deploy"
        description = "Deploy ${svc.name} into the repo."
        dependsOn("generate${svc.name}")
        outputs.upToDateWhen { false }
        onlyIf { !svc.isWebhook }

        doFirst {
            delete(layout.projectDirectory.dir("repo/Adyen/services/$serviceName"))
        }

        from(layout.buildDirectory.dir("services/${svc.id}/openapi_client/api"))
        include("*_api.py")
        into(layout.projectDirectory.dir("repo/Adyen/services/$serviceName"))

        from(layout.buildDirectory.dir("services/${svc.id}/api")) {
            include("api-single.py")
            rename("api-single.py", "__init__.py")
        }
    }

    tasks.named(svc.id) {
        dependsOn(deployServices)
    }
}

// TODO: Review how to generalize this to other libs
/**
 * Configures a service lifecycle tasks to perform a final sanity check: ensure that given files exists at the expected location.
 * @param serviceName the service to be checked
 * @param files the expected files
 */
fun assertServiceFilesExist(serviceId: String, files: List<String>) {
    tasks.named(serviceId) {
        val serviceName = serviceNaming[serviceId]!!
        // Hooks into this lifecycle task to do a sanity check: ensure that the given files
        // exists in the expected location
        doLast {
            files.forEach {
                assert(file("${layout.projectDirectory}/repo/Adyen/services/$serviceName/$it").exists())
            }
        }
    }
}

assertServiceFilesExist("checkout", listOf("payments_api.py", "__init__.py"))
assertServiceFilesExist("capital", listOf("__init__.py", "grants_api.py", "grant_offers_api.py", "grant_accounts_api.py"))
