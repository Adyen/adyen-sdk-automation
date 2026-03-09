import com.adyen.sdk.Service
import com.adyen.sdk.SdkAutomationExtension
import groovy.json.JsonOutput
import groovy.json.JsonSlurper
import org.openapitools.generator.gradle.plugin.tasks.GenerateTask
import java.util.Properties

apply(plugin = "org.openapi.generator")

val props = Properties()
rootProject.file("buildSrc/gradle.properties").inputStream().use { props.load(it) }
val openApiVersion: String? = props.getProperty("openapiGeneratorVersion")

repositories {
    mavenCentral()
}

// Create the extension
val sdkExtension = project.extensions.create<SdkAutomationExtension>("sdkAutomation")
sdkExtension.openApiVersion.set(openApiVersion)

// Helper to handle JSON casting
@Suppress("UNCHECKED_CAST")
fun <T> cast(obj: Any?): T = obj as T

// list of services to be generated
// services are APIs with multiple tags: the generation will create a service class/file for each tag
// smallServices are APIs with a single tag 'General': the generation will create a single class/file
val servicesList = listOf(
    // Payments
    Service(name = "Checkout", version = 71),
    Service(name = "Payout", version = 68),
    Service(name = "Recurring", version = 68, small = true),
    Service(name = "BinLookup", version = 54, small = true),
    Service(name = "PosMobile", spec = "SessionService", version = 68, small = true),
    Service(name = "PaymentsApp", spec = "PaymentsAppService", version = 1, small = true),
    Service(name = "Disputes", spec = "DisputeService", version = 30, small = true),
    Service(name = "StoredValue", version = 46, small = true),
    // Classic Payments
    Service(name = "Payment", version = 68, small = true),
    // Management
    Service(name = "Management", version = 3),
    Service(name = "BalanceControl", version = 1, small = true),
    // Adyen for Platforms
    Service(name = "LegalEntityManagement", spec = "LegalEntityService", version = 4),
    Service(name = "BalancePlatform", version = 2),
    Service(name = "Transfers", spec = "TransferService", version = 4),
    Service(name = "DataProtection", version = 1, small = true),
    Service(name = "SessionAuthentication", version = 1),
    Service(name = "Capital", version = 1),
    // Webhooks
    Service(name = "ConfigurationWebhooks", spec = "BalancePlatformConfigurationNotification", version = 2),
    Service(name = "AcsWebhooks", spec = "BalancePlatformAcsNotification", version = 1),
    Service(name = "ReportWebhooks", spec = "BalancePlatformReportNotification", version = 1),
    Service(name = "TransferWebhooks", spec = "BalancePlatformTransferNotification", version = 4),
    Service(name = "TransactionWebhooks", spec = "BalancePlatformTransactionNotification", version = 4),
    Service(name = "ManagementWebhooks", spec = "ManagementNotificationService", version = 3),
    Service(name = "DisputeWebhooks", spec = "BalancePlatformDisputeNotification", version = 1),
    Service(
        name = "NegativeBalanceWarningWebhooks",
        spec = "BalancePlatformNegativeBalanceCompensationWarningNotification",
        version = 1
    ),
    Service(name = "BalanceWebhooks", spec = "BalancePlatformBalanceNotification", version = 1),
    Service(name = "TokenizationWebhooks", spec = "TokenizationNotification", version = 1),
    Service(
        name = "RelayedAuthorizationWebhooks",
        spec = "BalancePlatformRelayedAuthorisationNotification",
        version = 4
    )
)

sdkExtension.services.set(servicesList)
sdkExtension.smallServices.set(servicesList.filter { it.small })
sdkExtension.serviceNaming.set(servicesList.associate { it.id to it.name })
sdkExtension.serviceNamingCamel.set(servicesList.associate {
    it.id to (it.name.substring(0, 1).lowercase() + it.name.substring(1))
})
sdkExtension.generator.set(project.name)
sdkExtension.templates.set("templates")
sdkExtension.serviceName.set("")
sdkExtension.removeTags.set(true)

// Generate a full client for each service
servicesList.forEach { svc ->
    val generate = tasks.register("generate${svc.name}", GenerateTask::class) {
        println("Generating ${svc.name} Client...")
        group = "generate"
        description = "Generate a ${project.name} client for ${svc.name}."
        dependsOn("cloneRepo")
        dependsOn(":specs")

        generatorName.set(sdkExtension.generator)
        inputSpec.set("$rootDir/schema/json/${svc.filename}")
        outputDir.set("${project.layout.buildDirectory.get().asFile}/services/${svc.id}")
        templateDir.set("${projectDir}/repo/${sdkExtension.templates.get()}")
        engine.set("mustache")
        validateSpec.set(false)
        skipValidateSpec.set(true)
        reservedWordsMappings.set(
            mapOf(
                "configuration" to "configuration"
            )
        )
        additionalProperties.set(
            mapOf(
                "serviceName" to svc.name
            )
        )
        globalProperties.set(
            mapOf(
                "modelDocs" to "false",
                "modelTests" to "false"
            )
        )

        if (project.extra.has("configFile")) {
            configFile.set("$projectDir/repo/${project.extra["configFile"]}")
        }
    }

    tasks.register(svc.id) {
        group = "service"
        description = "Base task for ${svc.name}."
        dependsOn(generate)
    }
}

// generate all services
tasks.register("services") {
    description = "Generate code for multiple services."
    dependsOn(servicesList.map { it.id })
}

tasks.named("generateCheckout", GenerateTask::class) {
    if (project.name == "node") {
        // generator v5 does not support inlineSchemaNameMappings
        return@named
    }
    inlineSchemaNameMappings.set(
        mapOf(
            "PaymentRequest_paymentMethod" to "CheckoutPaymentMethod",
            "DonationPaymentRequest_paymentMethod" to "DonationPaymentMethod"
        )
    )
}

tasks.register<Exec>("cloneRepo") {
    group = "setup"
    val uri = "https://github.com/Adyen/adyen-${project.name}-api-library.git"
    val dest = "repo"
    description = "Clone this project's repository."
    commandLine("git", "clone", uri, "--single-branch", dest)
    outputs.dir(dest)
    onlyIf { !file(dest).exists() }
}

// Disable generator caching
tasks.withType(GenerateTask::class).configureEach {
    doFirst {
        println("Using OpenAPI Generator version ${sdkExtension.openApiVersion.get()}")
    }
    outputs.upToDateWhen { false }
    outputs.cacheIf { false }
}

val cleanTracked = tasks.register<Exec>("cleanTracked") {
    group = "clean"
    commandLine("git", "checkout", ".")
    workingDir("repo")
    onlyIf { file("repo").exists() }
}

val cleanUntracked = tasks.register<Exec>("cleanUntracked") {
    group = "clean"
    commandLine("git", "clean", "-f", "-d")
    workingDir("repo")
    onlyIf { file("repo").exists() }
}

tasks.register("cleanRepo") {
    group = "clean"
    description = "Clean this project state"
    val buildDir = layout.buildDirectory
    dependsOn(cleanTracked, cleanUntracked)
    doLast {
        delete(buildDir)
    }
}

tasks.register<Copy>("addPMTable") {
    dependsOn("cloneRepo")
    dependsOn(":pmTable")
    from(rootProject.file("PaymentMethodOverview.md"))
    into(layout.projectDirectory.dir("repo"))
}

// update OpenAPI file of the smallService to rename the tag from 'General' to the name of the API (i.e. Binlookup)
// this is necessary to generate the service/class file using the name of the API (instead of General)
sdkExtension.smallServices.get().forEach { svc ->
    val ungroup = tasks.register("ungroup${svc.name}") {
        group = "specs"
        description = "Update tags in ${svc.name}"
        dependsOn(":specs")
        onlyIf { sdkExtension.removeTags.get() }
        doLast {
            val specFile = file("$rootDir/schema/json/${svc.filename}")
            val json = cast<MutableMap<String, Any>>(JsonSlurper().parse(specFile))

            val paths = cast<Map<String, Any>>(json["paths"])
            paths.forEach { (_, endpoint) ->
                val methods = cast<Map<String, Any>>(endpoint)
                methods.forEach { (_, httpMethod) ->
                    val methodDetails = cast<MutableMap<String, Any>>(httpMethod)
                    if (methodDetails.containsKey("tags") && methodDetails["tags"] is List<*>) {
                        val tags = cast<List<String>>(methodDetails["tags"])
                        // Rename tag associated with endpoint
                        methodDetails["tags"] = tags.map { tag ->
                            if (tag == "General") svc.name else tag
                        }
                    }
                }
            }
            specFile.writeText(JsonOutput.prettyPrint(JsonOutput.toJson(json)))
        }
    }
    tasks.named("generate${svc.name}") { dependsOn(ungroup) }
}

// update OpenAPI file of the webhooks to add a custom extension 'x-webhook-root' to the model that represents the webhook payload
// this is necessary to generate the WebhookHandler that deserialises the Webhook models
servicesList.forEach { svc ->
    // unnecessary to create webhook-related tasks for services/specs not related to webhooks
    if (!svc.isWebhook) {
        return@forEach
    }
    val addWebhookExtension = tasks.register("addWebhookExtension${svc.name}") {
        group = "specs"
        description = "Add x-webhook-root extension to ${svc.name}"
        dependsOn(":specs")
        doLast {
            val specFile = file("$rootDir/schema/json/${svc.filename}")
            val json = cast<MutableMap<String, Any>>(JsonSlurper().parse(specFile))

            if (json.containsKey("components")) {
                val components = cast<Map<String, Any>>(json["components"])
                if (components.containsKey("schemas")) {
                    val schemas = cast<Map<String, Any>>(components["schemas"])
                    var addOnce = true
                    schemas.forEach { (schemaKey, schemaValue) ->
                        val schemaDetails = cast<MutableMap<String, Any>>(schemaValue)
                        val properties = cast<Map<String, Any>?>(schemaDetails["properties"])
                        // add 'x-webhook-root' to the webhook model (we find 'environment' and 'data' attributes)
                        if (properties?.containsKey("environment") == true && properties.containsKey("data")) {
                            schemaDetails["x-webhook-root"] = true
                        }
                        // add 'x-webhook-root' to RelayedAuthenticationRequest model (missing 'environment' and 'data' attributes)
                        // bespoke fix as the model doesn't adopt the standard schema
                        if (schemaKey == "RelayedAuthenticationRequest") {
                            schemaDetails["x-webhook-root"] = true
                        }
                        // add 'x-webhook-root' to DisputeNotificationRequest model
                        // bespoke fix as the model doesn't adopt the standard schema (missing 'environment' attribute)
                        if (schemaKey == "DisputeNotificationRequest") {
                            schemaDetails["x-webhook-root"] = true
                        }
                        // add 'x-webhook-root' to RelayedAuthorisationRequest model (missing 'data' attributes)
                        // bespoke fix as the model doesn't adopt the standard schema
                        if (schemaKey == "RelayedAuthorisationRequest") {
                            schemaDetails["x-webhook-root"] = true
                        }

                        // Workaround
                        // Mark one model `{{#x-has-at-least-one-webhook-root}}` as true. I could not extend this property at the root-level.
                        // Context: {{#models}}{{#model.vendorExtensions.x-webhook-root}} -> {{#first}} won't work with multiple `x-webhook-root` extensions
                        if (addOnce) {
                            schemaDetails["x-has-at-least-one-webhook-root"] = true
                            addOnce = false
                        }
                    }
                }
            }

            specFile.writeText(JsonOutput.prettyPrint(JsonOutput.toJson(json)))
        }
    }

    tasks.named("generate${svc.name}", GenerateTask::class) {
        println("Generating ${svc.name} Webhooks...")
        dependsOn(addWebhookExtension)
    }
}
