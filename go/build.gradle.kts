import com.adyen.sdk.SdkAutomationExtension
import com.adyen.sdk.configureGoServices
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
sdkAutomation.preserveOpenApiVersion.set(true)

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

// Package, directory, service name, error model and deployment of each service (GoServiceLayout).
configureGoServices(sdkAutomation.services.get())

// Generation fixtures: small specs that pin how the generator and templates handle each schema
// construct. Models are deployed next to handwritten tests in repo/tests/generation/fixtures.
val fixtureSpec = layout.projectDirectory.file("fixtures/GenerationFixtures.json")
val stagedFixtureSpec = layout.buildDirectory.file("specs/GenerationFixtures.json")
val prepareFixtureSpec = tasks.register("prepareFixtureSpec") {
    group = "specs"
    description = "Stage the generation fixture spec like a Go service spec."
    inputs.file(fixtureSpec)
    outputs.file(stagedFixtureSpec)
    doLast {
        val target = stagedFixtureSpec.get().asFile
        target.parentFile.mkdirs()
        target.writeText(
            com.adyen.sdk.SpecProcessor.process(
                fixtureSpec.asFile.readText(),
                com.adyen.sdk.SpecProcessor.Options(downgradeOpenApiVersion = false, normalizeForOpenApi31 = true)
            )
        )
    }
}
val generateFixtures = tasks.register<GenerateTask>("generateFixtures") {
    group = "generate"
    description = "Generate the Go generation fixtures."
    dependsOn("cloneRepo", prepareFixtureSpec)
    generatorName.set(sdkAutomation.generator)
    inputSpec.set(stagedFixtureSpec.map { it.asFile.absolutePath })
    outputDir.set(layout.buildDirectory.dir("fixtures").map { it.asFile.absolutePath })
    templateDir.set("$projectDir/repo/${sdkAutomation.templates.get()}")
    configFile.set("$projectDir/repo/${project.extra["configFile"]}")
    packageName.set("fixtures")
    engine.set("mustache")
    validateSpec.set(false)
    skipValidateSpec.set(true)
    additionalProperties.set(mapOf("serviceName" to "Fixtures"))
}
val deployFixtures = tasks.register<Copy>("deployFixtures") {
    group = "deploy"
    description = "Copy the generated fixture models into the repo."
    dependsOn(generateFixtures)
    outputs.upToDateWhen { false }
    val target = layout.projectDirectory.dir("repo/tests/generation/fixtures")
    doFirst {
        target.asFile.listFiles()?.filter { it.name.startsWith("model_") }?.forEach { it.delete() }
    }
    from(layout.buildDirectory.dir("fixtures"))
    include("model_*.go")
    into(target)
}
tasks.register("fixtures") {
    group = "service"
    description = "Generate and deploy the Go generation fixtures."
    dependsOn(deployFixtures)
}
