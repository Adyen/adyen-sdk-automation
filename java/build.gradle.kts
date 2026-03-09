import com.adyen.sdk.Service
import com.adyen.sdk.SdkAutomationExtension
import org.openapitools.generator.gradle.plugin.tasks.GenerateTask

plugins {
    id("adyen.sdk-automation-conventions")
}

val sdkAutomation = extensions.getByType<SdkAutomationExtension>()
sdkAutomation.generator.set("java")

val services = sdkAutomation.services.get()
val serviceNaming = sdkAutomation.serviceNaming.get()

tasks.withType(GenerateTask::class).configureEach {
    val serviceId = project.name.lowercase()
    val modelNamespace = "com.adyen.model.${serviceId}"
    
    templateDir.set("$projectDir/repo/templates-v7")
    library.set("jersey3")
    modelPackage.set(modelNamespace.replace('/', '.'))
    apiPackage.set("com.adyen.service.${serviceId}")
    apiNameSuffix.set("Api")
    additionalProperties.putAll(mapOf(
        "dateLibrary" to "java8",
        "openApiNullable" to "false",
        "enumPropertyNaming" to "legacy",
        "javaxPackage" to "jakarta",
        "containerDefaultToNull" to "true"
    ))

    if (serviceId.endsWith("webhooks")) {
        // for webhooks only apply extra config.yaml (to generate WebhookHandler)
        configFile.set("$projectDir/config.yaml")
    } else {
        // for APIs only add custom code to handle nullable properties
        additionalProperties.put("handleNullableProperties", true)
    }
}

// Deployment: copy and rename models/services
services.forEach { svc ->
    val serviceName = serviceNaming[svc.id]!!
    val serviceId = serviceName.lowercase()

    // words replacement to enforce naming conventions (after code generation)
    val replaceReservedWords = { directory: Any ->
        fileTree(directory).matching { include("**/*.java") }.forEach { file ->
            var text = file.readText()
            val replaceFromTo = mapOf(
                "wwWAuthenticate" to "wwwAuthenticate"
            )

            replaceFromTo.forEach { (from, to) ->
                text = text.replace(from, to)
            }
            file.writeText(text)
        }
    }

    // Copy models
    val deployModels = tasks.register<Copy>("deploy${svc.name}Models") {
        group = "deploy"
        description = "Deploy ${svc.name} models into the repo."
        dependsOn("generate${svc.name}")
        outputs.upToDateWhen { false }

        // delete existing models
        doFirst {
            delete(layout.projectDirectory.dir("repo/src/main/java/com/adyen/model/${serviceId}"))
        }

        // copy newly generated models
        from(layout.buildDirectory.dir("services/${svc.id}/src/main/java/com/adyen/model"))
        into(layout.projectDirectory.dir("repo/src/main/java/com/adyen/model"))

        // post processing
        doLast {
            replaceReservedWords(layout.projectDirectory.dir("repo/src/main/java/com/adyen/model/${serviceId}"))
        }
    }

    // Copy services
    val deployServices = tasks.register<Copy>("deploy${svc.name}Services") {
        group = "deploy"
        description = "Deploy ${svc.name} services into the repo."
        dependsOn(deployModels)
        outputs.upToDateWhen { false }

        // delete existing services
        doFirst {
            delete(layout.projectDirectory.dir("repo/src/main/java/com/adyen/service/${serviceId}"))
        }

        // copy newly generated services
        from(layout.buildDirectory.dir("services/${svc.id}/src/main/java/com/adyen/service/${serviceId}"))
        into(layout.projectDirectory.dir("repo/src/main/java/com/adyen/service/${serviceId}"))

        // post processing
        doLast {
            replaceReservedWords(layout.projectDirectory.dir("repo/src/main/java/com/adyen/service/${serviceId}"))
        }
    }

    // Copy serializers
    val deploySerializers = tasks.register<Copy>("deploy${svc.name}Serializers") {
        group = "deploy"
        description = "Deploy ${svc.name} serializers into the repo."
        dependsOn(deployServices)
        outputs.upToDateWhen { false }

        // copy serializer JSON.java from service folder (if found) into model folder
        val jsonJavaFileModelFolder = layout.buildDirectory.file("services/${svc.id}/src/main/java/com/adyen/service/JSON.java")

        from(jsonJavaFileModelFolder)
        into(layout.projectDirectory.file("repo/src/main/java/com/adyen/model/${serviceId}"))

        // copy serializer JSON.java from adyen folder (if found) into model folder
        val jsonJavaFileAdyenFolder = layout.buildDirectory.file("services/${svc.id}/src/main/java/com/adyen/JSON.java")

        from(jsonJavaFileAdyenFolder)
        into(layout.projectDirectory.file("repo/src/main/java/com/adyen/model/${serviceId}"))
    }

    // Copy Webhook handlers
    val deployWebhookHandlers = tasks.register("deploy${svc.name}Handlers") {
        group = "deploy"
        description = "Move ${svc.name} handlers into the repo."
        dependsOn(deployServices)
        outputs.upToDateWhen { false }

        doLast {
            // find generated WebhookHandler.java
            val sourceFile = layout.projectDirectory.file("repo/src/main/java/com/adyen/model/WebhookHandler.java").asFile
            // move to service folder and rename (i.e. WebhookHandler.java to ConfigurationWebhooksHandler.java)
            val targetDir = layout.projectDirectory.file("repo/src/main/java/com/adyen/model/${serviceId}").asFile
            val targetFile = File(targetDir, "${svc.name}Handler.java")

            if (sourceFile.exists()) {
                sourceFile.renameTo(targetFile)
                println("Moved $sourceFile to $targetFile")
            } else {
                println("Source file does not exist: $sourceFile")
            }
        }
    }

    tasks.named(svc.id) {
        dependsOn(deployModels, deployServices, deploySerializers, deployWebhookHandlers)
    }
}

// Test binlookup generation
tasks.named("binlookup") {
    doLast {
        assert(file("${layout.projectDirectory}/repo/src/main/java/com/adyen/model/binlookup/Amount.java").exists())
        assert(file("${layout.projectDirectory}/repo/src/main/java/com/adyen/service/BinLookupApi.java").exists())
        // verify DefaultApi class no longer exists (it has been renamed to BinLookupApi)
        assert(!file("${layout.projectDirectory}/repo/src/main/java/com/adyen/service/binlookup/DefaultApi.java").exists())
    }
}
// Test checkout generation
tasks.named("checkout") {
    doLast {
        assert(file("${layout.projectDirectory}/repo/src/main/java/com/adyen/model/checkout/Amount.java").exists())
        assert(file("${layout.projectDirectory}/repo/src/main/java/com/adyen/service/checkout/PaymentsApi.java").exists())
    }
}
// Test acswebhooks generation
tasks.named("acswebhooks") {
    doLast {
        assert(file("${layout.projectDirectory}/repo/src/main/java/com/adyen/model/acswebhooks/Amount.java").exists())
        // verify no service package is created for a webhook
        assert(!file("${layout.projectDirectory}/repo/src/main/java/com/adyen/service/acswebhooks").exists())
        // verify no API class is created for a webhook
        assert(!file("${layout.projectDirectory}/repo/src/main/java/com/adyen/service/AcsWebhooksApi.java").exists())
        // verify Webhook Handler is created
        assert(file("${layout.projectDirectory}/repo/src/main/java/com/adyen/model/acswebhooks/AcsWebhooksHandler.java").exists())
    }
}

// Test balanceplatform generation
tasks.named("balanceplatform") {
    doLast {
        // HTTP header not found in signature
        val fileContent = file("${layout.projectDirectory}/repo/src/main/java/com/adyen/service/balanceplatform/ScaAssociationManagementApi.java").readText()
        assert(!fileContent.contains("wwwAuthenticate")) { "'wwwAuthenticate' (HTTP header) should not be part of a method signature in ScaAssociationManagementApi.java" }
    }
}

// Test RelayedAuthorization Webhooks generation
tasks.named("relayedauthorizationwebhooks") {
    doLast {
        // verify Webhook Handler is created
        assert(file("${layout.projectDirectory}/repo/src/main/java/com/adyen/model/relayedauthorizationwebhooks/RelayedAuthorizationWebhooksHandler.java").exists())
        // verify model is created
        assert(file("${layout.projectDirectory}/repo/src/main/java/com/adyen/model/relayedauthorizationwebhooks/RelayedAuthorisationRequest.java").exists())

        val fileContent = file("${layout.projectDirectory}/repo/src/main/java/com/adyen/model/relayedauthorizationwebhooks/RelayedAuthorizationWebhooksHandler.java").readText()
        assert(fileContent.contains("getRelayedAuthorisationRequest")) { "'getRelayedAuthorisationRequest' method not found in RelayedAuthorizationWebhooksHandler.java" }
    }
}

tasks.named("capital") {
    doLast {
        assert(file("${layout.projectDirectory}/repo/src/main/java/com/adyen/model/capital/Amount.java").exists())
        assert(file("${layout.projectDirectory}/repo/src/main/java/com/adyen/service/capital/GrantsApi.java").exists())
        assert(file("${layout.projectDirectory}/repo/src/main/java/com/adyen/service/capital/GrantOffersApi.java").exists())
        assert(file("${layout.projectDirectory}/repo/src/main/java/com/adyen/service/capital/GrantAccountsApi.java").exists())
    }
}
