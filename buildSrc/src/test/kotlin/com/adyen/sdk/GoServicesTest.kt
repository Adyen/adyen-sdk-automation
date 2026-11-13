package com.adyen.sdk

import org.assertj.core.api.Assertions.assertThat
import org.gradle.api.Project
import org.gradle.testfixtures.ProjectBuilder
import org.junit.jupiter.api.Test
import org.openapitools.generator.gradle.plugin.tasks.GenerateTask
import java.io.File

class GoServicesTest {

    private val spec = """
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
                .writeText(spec)
            val prepare = project.tasks.getByName("prepareSpec${svc.name}")
            prepare.actions.forEach { it.execute(prepare) }
        }
        return project
    }

    private fun Project.generate(name: String) = tasks.getByName("generate$name") as GenerateTask

    @Test
    fun `each service gets its own package and service name`() {
        val project = goProject()

        val expected = mapOf(
            "Transfers" to ("transfers" to "Transfers"),
            "Checkout" to ("checkout" to "Checkout"),
            "Payment" to ("payments" to ""),
            "LegalEntityManagement" to ("legalentity" to "LegalEntity"),
            "AcsWebhooks" to ("acswebhook" to "AcsWebhooks"),
        )
        expected.forEach { (name, values) ->
            val (packageName, serviceName) = values
            val task = project.generate(name)
            assertThat(task.packageName.get()).`as`("$name package").isEqualTo(packageName)
            val properties = task.additionalProperties.get()
            assertThat(properties).`as`("$name properties").containsEntry("serviceName", serviceName)
            // Every service returns *common.APIError; no service-specific error model.
            assertThat(properties).`as`("$name properties").doesNotContainKey("hasRestServiceError")
        }
    }

    @Test
    fun `webhook packages render the handler instead of the client`() {
        val project = goProject()

        mapOf(
            "AcsWebhooks" to "webhook_handler.go",
            "Checkout" to "client.go",
            "Payment" to "client.go",
        ).forEach { (name, supportingFile) ->
            assertThat(project.generate(name).globalProperties.get())
                .`as`("$name global properties")
                .containsEntry("supportingFiles", supportingFile)
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
                .isEqualTo(File(project.projectDir, "repo/$directory").canonicalFile)
            val serviceTask = project.tasks.getByName(name.lowercase())
            assertThat(serviceTask.taskDependencies.getDependencies(serviceTask)).contains(deploy)
        }
    }
}
