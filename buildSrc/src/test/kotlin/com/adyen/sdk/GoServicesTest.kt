package com.adyen.sdk

import org.assertj.core.api.Assertions.assertThat
import org.gradle.api.Project
import org.gradle.testfixtures.ProjectBuilder
import org.junit.jupiter.api.Test
import org.openapitools.generator.gradle.plugin.tasks.GenerateTask
import java.io.File

class GoServicesTest {

    private val restServiceErrorSpec = """
        { "openapi": "3.1.0", "paths": { "/transfers": { "post": { "responses": {
          "422": { "content": { "application/json": { "schema": { "${'$'}ref": "#/components/schemas/RestServiceError" } } } }
        } } } } }
    """.trimIndent()

    private val serviceErrorSpec = """
        { "openapi": "3.1.0", "paths": { "/payments": { "post": { "responses": {
          "422": { "content": { "application/json": { "schema": { "${'$'}ref": "#/components/schemas/ServiceError" } } } }
        } } } } }
    """.trimIndent()

    /** A Go project configured like go/build.gradle.kts, with each service's spec staged. */
    private fun goProject(): Project {
        val project = ProjectBuilder.builder().withName("go").build()
        File(project.projectDir, "config/services.json").apply { parentFile.mkdirs() }.writeText(
            """
            { "services": [
              { "name": "Transfers", "version": 4 },
              { "name": "Checkout", "version": 72 },
              { "name": "Payment", "version": 68, "small": true },
              { "name": "LegalEntityManagement", "version": 3 },
              { "name": "AcsWebhooks", "version": 1 }
            ] }
            """.trimIndent()
        )
        project.pluginManager.apply("adyen.sdk-automation-conventions")
        val extension = project.extensions.getByType(SdkAutomationExtension::class.java)
        extension.removeTags.set(false)
        extension.preserveOpenApiVersion.set(true)
        val services = extension.services.get()
        project.configureGoServices(services)

        services.forEach { svc ->
            File(project.rootDir, "schema/json/${svc.filename}").apply { parentFile.mkdirs() }
                .writeText(if (svc.name == "Transfers") restServiceErrorSpec else serviceErrorSpec)
            val prepare = project.tasks.getByName("prepareSpec${svc.name}")
            prepare.actions.forEach { it.execute(prepare) }
        }
        return project
    }

    private fun Project.generate(name: String) = tasks.getByName("generate$name") as GenerateTask

    @Test
    fun `each service gets its own package, service name and error model`() {
        val project = goProject()

        val expected = mapOf(
            "Transfers" to Triple("transfers", "Transfers", true),
            "Checkout" to Triple("checkout", "Checkout", false),
            "Payment" to Triple("payments", "", false),
            "LegalEntityManagement" to Triple("legalentity", "LegalEntity", false),
            "AcsWebhooks" to Triple("acswebhook", "AcsWebhooks", false),
        )
        expected.forEach { (name, values) ->
            val (packageName, serviceName, hasRestServiceError) = values
            val task = project.generate(name)
            assertThat(task.packageName.get()).`as`("$name package").isEqualTo(packageName)
            val properties = task.additionalProperties.get()
            assertThat(properties).`as`("$name properties").containsEntry("serviceName", serviceName)
            if (hasRestServiceError) {
                assertThat(properties).`as`("$name properties").containsEntry("hasRestServiceError", "true")
            } else {
                assertThat(properties).`as`("$name properties").doesNotContainKey("hasRestServiceError")
            }
        }
    }

    @Test
    fun `each service deploys into its own directory`() {
        val project = goProject()

        mapOf(
            "Payment" to "payments",
            "LegalEntityManagement" to "legalentity",
            "AcsWebhooks" to "acswebhook",
            "Checkout" to "checkout",
        ).forEach { (name, directory) ->
            val deploy = project.tasks.getByName("deploy$name") as org.gradle.api.tasks.Copy
            assertThat(deploy.destinationDir.canonicalFile)
                .isEqualTo(File(project.projectDir, "repo/src/$directory").canonicalFile)
            val serviceTask = project.tasks.getByName(name.lowercase())
            assertThat(serviceTask.taskDependencies.getDependencies(serviceTask)).contains(deploy)
        }
    }
}
