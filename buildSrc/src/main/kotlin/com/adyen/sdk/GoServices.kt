package com.adyen.sdk

import org.gradle.api.Project
import org.gradle.api.tasks.Copy
import org.openapitools.generator.gradle.plugin.tasks.GenerateTask

/** Name of the shared error model that Go maps non-2xx responses to. */
const val REST_SERVICE_ERROR = "RestServiceError"

/**
 * Configures generation and deployment of every Go service from its [GoServiceLayout].
 *
 * Must run after the conventions plugin registered `generate<Service>` and `<id>` tasks.
 */
fun Project.configureGoServices(services: List<Service>) {
    services.forEach { svc ->
        val goLayout = GoServiceLayout.of(svc)
        val stagedSpec = layout.buildDirectory.file("specs/${svc.filename}")

        val generate = tasks.named("generate${svc.name}", GenerateTask::class.java) {
            packageName.set(goLayout.packageName)
            additionalProperties.put("serviceName", goLayout.serviceName)
            globalProperties.put("supportingFiles", goLayout.supportingFile)
            // The generator only adds files, so outputs of earlier runs (removed models, a
            // client.go from before a supporting file change) would otherwise be deployed.
            doFirst { project.delete(outputDir.get()) }
            // Read at execution time, after prepareSpec<Service> staged the spec.
            additionalProperties.putAll(stagedSpec.map { spec ->
                if (SpecProcessor.respondsWithSchema(spec.asFile.readText(), REST_SERVICE_ERROR)) {
                    mapOf("hasRestServiceError" to "true")
                } else {
                    emptyMap()
                }
            })
        }

        val target = layout.projectDirectory.dir("repo/${goLayout.directory}")
        val deploy = tasks.register("deploy${svc.name}", Copy::class.java) {
            group = "deploy"
            description = "Copy ${svc.name} files into ${goLayout.directory}."
            dependsOn(generate)
            outputs.upToDateWhen { false }
            doFirst {
                target.asFile.listFiles()?.forEach { it.deleteRecursively() }
            }
            val generated = layout.buildDirectory.dir("services/${svc.id}")
            from(generated)
            // The generator creates an empty api/ directory even when openapi.yaml is not rendered.
            includeEmptyDirs = false
            exclude { element ->
                element.relativePath.pathString == GoServiceLayout.CLIENT &&
                    !goLayout.deploysClient(generated.get().asFile.list()?.toList().orEmpty())
            }
            into(target)
        }

        tasks.named(svc.id) {
            dependsOn(deploy)
        }
    }
}
