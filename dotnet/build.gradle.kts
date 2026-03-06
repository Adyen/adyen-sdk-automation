import com.adyen.sdk.Service
import com.adyen.sdk.SdkAutomationExtension
import org.openapitools.generator.gradle.plugin.tasks.GenerateTask

plugins {
    id("adyen.sdk-automation-conventions")
}

val sdkAutomation = extensions.getByType<SdkAutomationExtension>()
sdkAutomation.generator.set("csharp")
sdkAutomation.templates.set("templates-v7/csharp/libraries/generichost")

val services = sdkAutomation.services.get()
val serviceNamingMap = sdkAutomation.serviceNaming.get()

services.forEach { svc ->
    val serviceName = serviceNamingMap[svc.id]!!

    // Function to replace reserved words for a given directory.
    val replaceReservedWords = { directory: Any ->
        fileTree(directory).matching { include("**/*.cs") }.forEach { file ->
            var text = file.readText()

            // See list of reserved words: https://github.com/OpenAPITools/openapi-generator/blob/master/docs/generators/csharp.md#reserved-words
            val replaceFromTo = mapOf(
                "VarEnvironment" to "Environment",
                "varEnvironment" to "environment",
                "VarVersion" to "Version",
                "varVersion" to "version",
                "VarTimeZone" to "TimeZone",
                "varTimeZone" to "timeZone",
                "VarConfiguration" to "Configuration",
                "varConfiguration" to "configuration",
                "wWWAuthenticate" to "wwwAuthenticate"
            )

            // Replaces reserved words with the name without the `Var` or `var`-prefix.
            replaceFromTo.forEach { (from, to) ->
                if (text.contains(from)) {
                    text = text.replace(from, to)
                }
            }

            file.writeText(text)
        }
    }

    // Generation
    tasks.named<GenerateTask>("generate${svc.name}") {
        println("Generating ${svc.name}...")

        // Sets suffix of api.
        apiNameSuffix.set("Service")

        // Sets apiPackage name for Services.
        apiPackage.set("${svc.name}.Services")

        // Sets modelPackageName.
        modelPackage.set("${svc.name}.Models")

        // Use typeMappings, Set<> is not a valid object in .NET.
        typeMappings.set(mapOf("set" to "HashSet"))

        // Use additionalProperties
        additionalProperties.putAll(mapOf(
            "targetFramework" to "net8.0",
            "library" to "generichost",
            "packageName" to "Adyen",
            "corePackageName" to "Core",
            "apiName" to svc.name,
            "caseInsensitiveResponseHeaders" to "false",
            "equatable" to "false",
            "serviceName" to serviceName,
            "nullableReferenceTypes" to "true",
            "useDateTimeOffset" to "true",
            "useOneOfDiscriminatorLookup" to "true"
        ))

        configFile.set("$projectDir/config.yaml")
    }

    val deployModels = tasks.register<Sync>("generate${svc.name}Models") {
        println("Moving ${svc.name}-Models...")
        group = "deploy"
        description = "Move ${svc.name} models into the repo."
        dependsOn("generate${svc.name}")
        outputs.upToDateWhen { false }

        // Delete existing /Models directory.
        doFirst {
            delete(layout.projectDirectory.dir("repo/Adyen/$serviceName/Models"))
        }

        from(layout.buildDirectory.dir("services/${svc.id}/src/Adyen/$serviceName.Models")) {
            eachFile {
                replaceReservedWords(this.file)
            }
        }
        into(layout.projectDirectory.dir("repo/Adyen/$serviceName/Models"))
    }

    val deployServices = tasks.register<Sync>("generate${svc.name}Services") {
        println("Moving ${svc.name}-Services...")
        group = "deploy"
        description = "Move ${svc.name} into the repo."
        dependsOn(deployModels)
        outputs.upToDateWhen { false }
        onlyIf { !svc.isWebhook } // Skip webhooks - This task is for generating service classes only, see deployWebhookHandlers instead.

        // Delete existing /Services directory.
        doFirst {
            delete(layout.projectDirectory.dir("repo/Adyen/$serviceName/Services"))
        }

        from(layout.buildDirectory.dir("services/${svc.id}/src/Adyen/$serviceName.Services")) {
            exclude("IApi.cs")
            eachFile {
                replaceReservedWords(this.file)
            }
        }
        into(layout.projectDirectory.dir("repo/Adyen/$serviceName/Services"))
    }

    val deployClients = tasks.register<Sync>("generate${svc.name}Clients") {
        println("Moving ${svc.name}-Clients...")
        group = "deploy"
        description = "Move ${svc.name} into the repo."
        dependsOn(deployServices)
        outputs.upToDateWhen { false }

        // Delete existing /Clients directory.
        doFirst {
            delete(layout.projectDirectory.dir("repo/Adyen/$serviceName/Clients"))
        }

        from(layout.buildDirectory.dir("services/${svc.id}/src/Adyen/Client")) {
            include("HostConfiguration.cs", "ClientUtils.cs", "JsonSerializerOptionsProvider.cs", "ApiKeyToken.cs")
            eachFile {
                replaceReservedWords(this.file)

                // Do not include the `Adyen.{{Webhook}}.Services` as namespace for webhooks.
                if (this.name == "HostConfiguration.cs" && serviceName.endsWith("Webhooks")) {
                    this.file.writeText(this.file.readText().replace("using Adyen.$serviceName.Services;", ""))
                    println("Removed Adyen.$serviceName.Services namespace in HostConfiguration.cs")
                }
            }
        }

        doLast {
            // Move AdyenOptionsProvider.cs to `/Client` folder
            moveAdyenOptionsProviderFile(svc, serviceName)
        }
        into(layout.projectDirectory.dir("repo/Adyen/$serviceName/Client"))
    }

    val deployExtensions = tasks.register<Sync>("generate${svc.name}Extensions") {
        println("Moving ${svc.name}-Extensions...")
        group = "generate"
        description = "Move ${svc.name} into the repo."
        dependsOn(deployClients)
        outputs.upToDateWhen { false }

        // Delete existing /Extensions directory.
        doFirst {
            delete(layout.projectDirectory.dir("repo/Adyen/$serviceName/Extensions"))
        }

        from(layout.buildDirectory.dir("services/${svc.id}/src/Adyen/Extensions")) {
            include("IHostBuilderExtensions.cs", "IServiceCollectionExtensions.cs")
            rename("IHostBuilderExtensions.cs", "HostBuilderExtensions.cs")
            rename("IServiceCollectionExtensions.cs", "ServiceCollectionExtensions.cs")
        }
        into(layout.projectDirectory.dir("repo/Adyen/$serviceName/Extensions"))
    }

    if (project.hasProperty("documentation.generation.enabled") && project.property("documentation.generation.enabled").toString().toBoolean()) {
        // generate docs (when flag is enabled)
        tasks.register<Sync>("generate${svc.name}Documentation") {
            println("Moving ${svc.name}-Documentation...")
            group = "generate"
            description = "Move ${svc.name} into the repo."
            dependsOn(deployServices)
            outputs.upToDateWhen { false }

            doFirst {
                // Delete existing /docs directory.
                delete(layout.projectDirectory.dir("repo/docs/$serviceName"))

                val docsDirectory = layout.projectDirectory.dir("repo/docs").asFile

                // Create /docs directory if it doesn't exist.
                if (!docsDirectory.exists()) {
                    docsDirectory.mkdirs()
                    println("Created /docs directory: $docsDirectory")
                }
            }

            from(layout.buildDirectory.dir("services/${svc.id}/docs/apis"))
            into(layout.projectDirectory.dir("repo/docs/$serviceName"))
        }
    }

    val deployWebhookHandlers = tasks.register("generate${svc.name}WebhookHandlers") {
        group = "deploy"
        description = "Move ${svc.name} handlers into the repo."
        dependsOn(deployModels)
        outputs.upToDateWhen { false }

        doLast {
            if (serviceName.endsWith("Webhooks")) {
                moveWebhookHandlerFile(svc, serviceName)
                moveHmacKeyTokenFile(svc, serviceName)
            }
        }
    }

    tasks.named(svc.id) {
        dependsOn(deployModels, deployServices, deployClients, deployExtensions, deployWebhookHandlers)
    }
}

fun moveWebhookHandlerFile(svc: Service, serviceName: String) {
    // Find generated WebhookHandler.cs.
    val webhookHandlerFile = layout.projectDirectory.file("build/services/${svc.id}/src/Adyen/SupportingFiles/WebhookHandler.cs").asFile
    // Move file to the /Handlers directory and prefix with the serviceName (e.g. WebhookHandler.cs -> `Configuration`WebhooksHandler.cs).
    val handlerDirectory = layout.projectDirectory.file("repo/Adyen/$serviceName/Handlers").asFile

    // Create /Handlers directory if it doesn't exist.
    if (!handlerDirectory.exists()) {
        handlerDirectory.mkdirs()
    }

    val targetFile = File(handlerDirectory, "${svc.name}Handler.cs")

    if (webhookHandlerFile.exists()) {
        webhookHandlerFile.renameTo(targetFile)
        println("Moved $webhookHandlerFile to $targetFile")
    } else {
        println("Source file does not exist: $webhookHandlerFile")
    }
}

fun moveHmacKeyTokenFile(svc: Service, serviceName: String) {
    // Find generated HmacKeyToken.cs.
    val hmacKeyTokenFile = layout.projectDirectory.file("build/services/${svc.id}/src/Adyen/SupportingFiles/HmacKeyToken.cs").asFile

    // Move `HmacKeyToken.cs` to the /Client directory
    val clientDirectory = layout.projectDirectory.file("repo/Adyen/$serviceName/Client").asFile

    // Create /Client directory if it doesn't exist.
    if (!clientDirectory.exists()) {
        clientDirectory.mkdirs()
    }

    val targetFile = File(clientDirectory, "HmacKeyToken.cs")

    if (hmacKeyTokenFile.exists()) {
        hmacKeyTokenFile.renameTo(targetFile)
        println("Moved $hmacKeyTokenFile to $targetFile")
    } else {
        println("Source file does not exist: $hmacKeyTokenFile")
    }
}

fun moveAdyenOptionsProviderFile(svc: Service, serviceName: String) {
    // Find generated AdyenOptionsProvider.cs.
    val adyenOptionsProviderFile = layout.projectDirectory.file("build/services/${svc.id}/src/Adyen/SupportingFiles/AdyenOptionsProvider.cs").asFile

    // Move `AdyenOptionsProvider.cs` to the /Client directory
    val clientDirectory = layout.projectDirectory.file("repo/Adyen/$serviceName/Client").asFile

    // Create /Client directory if it doesn't exist.
    if (!clientDirectory.exists()) {
        clientDirectory.mkdirs()
    }

    val targetFile = File(clientDirectory, "AdyenOptionsProvider.cs")

    if (adyenOptionsProviderFile.exists()) {
        adyenOptionsProviderFile.renameTo(targetFile)
        println("Moved $adyenOptionsProviderFile to $targetFile")
    } else {
        println("Source file does not exist: $adyenOptionsProviderFile")
    }
}

// Test regular api services generation.
tasks.named("checkout") {
    doLast {
        val serviceName = "Checkout"

        // /Models folder
        assert(file("${layout.projectDirectory}/repo/Adyen/$serviceName/Models/Amount.cs").exists())

        // /Services folder
        assert(file("${layout.projectDirectory}/repo/Adyen/$serviceName/Services/PaymentsService.cs").exists())

        // /Client folder
        assert(file("${layout.projectDirectory}/repo/Adyen/$serviceName/Client/ApiKeyToken.cs").exists())
        assert(file("${layout.projectDirectory}/repo/Adyen/$serviceName/Client/ClientUtils.cs").exists())
        assert(file("${layout.projectDirectory}/repo/Adyen/$serviceName/Client/HostConfiguration.cs").exists())
        assert(file("${layout.projectDirectory}/repo/Adyen/$serviceName/Client/JsonSerializerOptionsProvider.cs").exists())
        assert(file("${layout.projectDirectory}/repo/Adyen/$serviceName/Client/AdyenOptionsProvider.cs").exists())

        // /Extensions folder
        assert(file("${layout.projectDirectory}/repo/Adyen/$serviceName/Extensions/HostBuilderExtensions.cs").exists())
        assert(file("${layout.projectDirectory}/repo/Adyen/$serviceName/Extensions/ServiceCollectionExtensions.cs").exists())

        // /Handlers folders should not exist for services.
        assert(!file("${layout.projectDirectory}/repo/Adyen/$serviceName/Handlers").exists())
    }
}

// Test webhook generation, supporting files WebhookHandler.cs and HmacKeyToken.cs both exist.
tasks.named("acswebhooks") {
    doLast {
        assert(file("${layout.projectDirectory}/repo/Adyen/AcsWebhooks/Models/Amount.cs").exists())

        assert(file("${layout.projectDirectory}/repo/Adyen/AcsWebhooks/Client/AdyenOptionsProvider.cs").exists())

        assert(!file("${layout.projectDirectory}/repo/Adyen/AcsWebhooks/Handlers/WebhookHandler.cs").exists())
        assert(!file("${layout.projectDirectory}/repo/Adyen/AcsWebhooks/Handlers/HmacKeyToken.cs").exists())

        assert(!file("${layout.projectDirectory}/repo/Adyen/AcsWebhooks/Services").exists())
        assert(!file("${layout.projectDirectory}/repo/Adyen/Service/AcsWebhooksService.cs").exists())
    }
}
