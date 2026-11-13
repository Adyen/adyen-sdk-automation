import com.adyen.sdk.Service
import com.adyen.sdk.SdkAutomationExtension
import com.adyen.sdk.SpecProcessor
import groovy.json.JsonSlurper
import org.gradle.api.GradleException
import org.openapitools.generator.gradle.plugin.tasks.GenerateTask
import java.util.Properties

apply(plugin = "org.openapi.generator")

val props = Properties()
val propsFile = rootProject.file("buildSrc/gradle.properties")
if (propsFile.exists()) {
    propsFile.inputStream().use { props.load(it) }
}
val openApiVersion: String? = System.getProperty("openapiGeneratorVersion")
    ?: project.findProperty("openapiGeneratorVersion") as String?
    ?: props.getProperty("openapiGeneratorVersion")

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
//
// The service catalog (config/services.json) is the single source of truth for the service matrix:
// both this build and the CI matrix (.github/scripts/resolve-matrix-inputs.sh) derive from it.
// A missing or malformed catalog fails every build at configuration time.
val catalogFile = rootProject.file("config/services.json")
val servicesList: List<Service> = try {
    val catalog = cast<Map<String, Any?>>(JsonSlurper().parse(catalogFile))
    cast<List<Map<String, Any?>>>(catalog["services"]).mapIndexed { index, entry ->
        try {
            Service(
                name = cast(entry["name"]),
                spec = entry["spec"] as String?,
                version = cast<Number>(entry["version"]).toInt(),
                small = entry["small"] as Boolean? ?: false,
                projects = cast(entry["projects"]),
                excludedProjects = cast(entry["excludedProjects"])
            )
        } catch (e: Exception) {
            throw GradleException("Invalid service entry #${index + 1} (${entry["name"] ?: "no name"}) in config/services.json: ${e.message}", e)
        }
    }
} catch (e: GradleException) {
    throw e
} catch (e: Exception) {
    throw GradleException(
        "Cannot load the service catalog at ${catalogFile.absolutePath}. " +
            "Fix config/services.json (see AGENTS.md). Cause: ${e.message}",
        e
    )
}

// When a service's `projects` is unset, it's available to all projects. Setting otherwise
// narrows its scope to only those in `projects`. A service's `excludedProjects` defines
// the projects it is omitted from.
val applicableServices = servicesList
    .filter { it.projects == null || it.projects.contains(project.name) }
    .filter { it.excludedProjects == null || !it.excludedProjects.contains(project.name) }

sdkExtension.services.set(applicableServices)
sdkExtension.smallServices.set(applicableServices.filter { it.small })
sdkExtension.serviceNaming.set(applicableServices.associate { it.id to it.name })
sdkExtension.serviceNamingCamel.set(applicableServices.associate {
    it.id to (it.name.substring(0, 1).lowercase() + it.name.substring(1))
})
sdkExtension.generator.set(project.name)
sdkExtension.templates.set("templates")
sdkExtension.serviceName.set("")
sdkExtension.removeTags.set(true)
sdkExtension.preserveOpenApiVersion.set(false)

// Generate a full client for each service
applicableServices.forEach { svc ->
    val stagedSpec = layout.buildDirectory.file("specs/${svc.filename}")
    val prepareSpec = tasks.register("prepareSpec${svc.name}") {
        group = "specs"
        description = "Stage the ${svc.name} spec for ${project.name} generation."
        dependsOn(":specs")
        val sourceSpec = rootProject.file("schema/json/${svc.filename}")
        // Read lazily: language build scripts adjust these after the plugin is applied.
        val options = sdkExtension.preserveOpenApiVersion.zip(sdkExtension.removeTags) { preserve, removeTags ->
            SpecProcessor.Options(
                downgradeOpenApiVersion = !preserve,
                generalTagReplacement = if (svc.small && removeTags) svc.name else null,
                markWebhookRoots = svc.isWebhook,
                normalizeForOpenApi31 = preserve,
                // Only the native 3.1 (Go) generation resolves inline enums into named types.
                nameArrayItemEnums = preserve,
                enumValuesAsVarNames = preserve,
            )
        }
        inputs.file(sourceSpec)
        inputs.property("options", options.map { it.toString() })
        outputs.file(stagedSpec)
        doLast {
            val target = stagedSpec.get().asFile
            target.parentFile.mkdirs()
            target.writeText(SpecProcessor.process(sourceSpec.readText(), options.get()))
        }
    }

    val generate = tasks.register("generate${svc.name}", GenerateTask::class) {
        println("Generating ${svc.name} Client...")
        group = "generate"
        description = "Generate a ${project.name} client for ${svc.name}."
        dependsOn("cloneRepo")
        dependsOn(prepareSpec)

        generatorName.set(sdkExtension.generator)
        inputSpec.set(stagedSpec.map { it.asFile.absolutePath })
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
    dependsOn(applicableServices.map { it.id })
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
        // The engine comes from the buildSrc classpath, which can differ from the project setting
        // when buildSrc/gradle.properties is not aligned (CI copies the project file into buildSrc).
        val loaded = org.openapitools.codegen.utils.ImplementationVersion.read()
        println("Using OpenAPI Generator version $loaded")
        val configured = sdkExtension.openApiVersion.orNull
        if (configured != null && configured != loaded) {
            logger.warn("OpenAPI Generator $configured is configured for ${project.name}, but $loaded is loaded")
        }
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
