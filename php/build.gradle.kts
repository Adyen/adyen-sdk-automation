import com.adyen.sdk.Service
import com.adyen.sdk.SdkAutomationExtension
import org.openapitools.generator.gradle.plugin.tasks.GenerateTask

plugins {
    id("adyen.sdk-automation-conventions")
}

val sdkAutomation = extensions.getByType<SdkAutomationExtension>()
sdkAutomation.removeTags.set(false)

val services = sdkAutomation.services.get()
val smallServices = sdkAutomation.smallServices.get()
val serviceNaming = sdkAutomation.serviceNaming.get().toMutableMap()

// Service renaming
serviceNaming.putAll(mapOf(
    "payment" to "Payments",
    "posterminalmanagement" to "POSTerminalManagement"
))

tasks.withType(GenerateTask::class).configureEach {
    val serviceId = sdkAutomation.serviceName.get() // Note: this might be empty if not set, original used project.extra["serviceId"]
    // In convention plugin, I didn't set serviceId in extension. I'll use property from GenerateTask if possible or just use current logic.
    // Actually, in convention plugin: tasks.register("generate${svc.name}") { ... }
    // We can get the service ID from the task name or just use a local variable in the loop.
}

// Subprojects often need to access the mapping.
// Let's use the local mapping for deployment.

// Deployment
services.filter { !it.small }.forEach { svc ->
    val deploy = tasks.register<Copy>("deploy${svc.name}") {
        group = "deploy"
        description = "Copy ${svc.name} files into the repo."
        dependsOn("generate${svc.name}")
        outputs.upToDateWhen { false }

        // Cleanup existing non-small Models and Services before generation
        doFirst {
            logger.lifecycle("Cleaning up existing files for ${svc.name}")
            delete(layout.projectDirectory.dir("repo/src/Adyen/Service/${svc.name}"))
            delete(layout.projectDirectory.dir("repo/src/Adyen/Model/${svc.name}"))
        }

        // Set the destination directory for copied files
        into(layout.projectDirectory.dir("repo/src/Adyen"))
        val sourcePath = "services/${svc.id}/lib"

        // Copy generated Model and Service PHP files
        from(layout.buildDirectory.dir(sourcePath)) {
            include("Model/**/*.php")
            include("Service/**/*.php")
        }

        // Copy ObjectSerializer.php to the specific model directory
        from(layout.buildDirectory.file("$sourcePath/ObjectSerializer.php")) {
            into("Model/" + serviceNaming[svc.id])
        }
    }

    tasks.named(svc.id) {
        dependsOn(deploy)
    }
}

// Deployment tasks for small services
smallServices.forEach { svc ->
    val serviceName = serviceNaming[svc.id]!!
    val deploy = tasks.register<Copy>("deploy${svc.name}") {
        group = "deploy"
        description = "Copy ${svc.name} files into the repo."
        dependsOn("generate${svc.name}")
        outputs.upToDateWhen { false }

        into(layout.projectDirectory.dir("repo/src/Adyen"))

        // Service
        val clazzName = "${serviceName}Api"
        from(layout.buildDirectory.file("services/${svc.id}/lib/Service/GeneralApi.php")) {
            rename("GeneralApi.php", "${clazzName}.php")
            filter { line ->
                line.replace("class GeneralApi", "class $clazzName")
                    .replace("GeneralApi constructor", "$clazzName constructor")
            }
            into("Service")
        }

        // Models
        from(layout.buildDirectory.dir("services/${svc.id}/lib/Model")) {
            include("**/*.php")
            into("Model")
        }

        // Serializer
        from(layout.buildDirectory.file("services/${svc.id}/lib/ObjectSerializer.php")) {
            into("Model/$serviceName")
        }
    }

    tasks.named(svc.id) {
        dependsOn(deploy)
    }
}

// Special configuration for PHP GenerateTasks
services.forEach { svc ->
    val serviceName = serviceNaming[svc.id]!!
    tasks.named<GenerateTask>("generate${svc.name}") {
        modelPackage.set("Model\\$serviceName")
        apiPackage.set("Service\\$serviceName")
        additionalProperties.putAll(mapOf(
            "variableNamingConvention" to "camelCase",
            "invokerPackage" to "Adyen",
            "packageName" to "Adyen"
        ))
        if (svc.small) {
            apiPackage.set("Service")
        }
    }
}

// Tests
tasks.named("binlookup") {
    doLast {
        assert(file("${layout.projectDirectory}/repo/src/Adyen/Model/BinLookup/Amount.php").exists())
        assert(file("${layout.projectDirectory}/repo/src/Adyen/Service/BinLookupApi.php").exists())
    }
}
tasks.named<Copy>("deployAcsWebhooks") {
    doLast {
        assert(file("${layout.projectDirectory}/repo/src/Adyen/Model/AcsWebhooks/Amount.php").exists())
        assert(file("${layout.projectDirectory}/repo/src/Adyen/Model/AcsWebhooks/ObjectSerializer.php").exists())
    }
}
tasks.named("deployCheckout") {
    doLast {
        assert(file("${layout.projectDirectory}/repo/src/Adyen/Model/Checkout/Amount.php").exists())
        assert(file("${layout.projectDirectory}/repo/src/Adyen/Service/Checkout/PaymentsApi.php").exists())
    }
}
tasks.named("payment") {
    doLast {
        assert(file("${layout.projectDirectory}/repo/src/Adyen/Model/Payments/Amount.php").exists())
        assert(file("${layout.projectDirectory}/repo/src/Adyen/Model/Payments/ObjectSerializer.php").exists())
        assert(file("${layout.projectDirectory}/repo/src/Adyen/Service/Payments/PaymentsApi.php").exists())
    }
}

tasks.named("capital") {
    doLast {
        assert(file("${layout.projectDirectory}/repo/src/Adyen/Model/Capital/Amount.php").exists())
        assert(file("${layout.projectDirectory}/repo/src/Adyen/Service/Capital/GrantsApi.php").exists())
        assert(file("${layout.projectDirectory}/repo/src/Adyen/Service/Capital/GrantOffersApi.php").exists())
        assert(file("${layout.projectDirectory}/repo/src/Adyen/Service/Capital/GrantAccountsApi.php").exists())
    }
}
