package com.adyen.sdk

import groovy.json.JsonOutput
import groovy.json.JsonSlurper

/**
 * Prepares a pristine OpenAPI spec for one generator project.
 *
 * All transformations run in memory on a copy, so the cloned source specs are never modified
 * and one project's preprocessing cannot leak into another project's input.
 */
object SpecProcessor {
    /** The version every project except those preserving the source version is generated from. */
    const val LEGACY_OPENAPI_VERSION = "3.0.0"

    data class Options(
        /** Rewrite the `openapi` field to [LEGACY_OPENAPI_VERSION]. */
        val downgradeOpenApiVersion: Boolean = true,
        /** When set, operations tagged `General` are re-tagged with this name. */
        val generalTagReplacement: String? = null,
        /** Annotate webhook payload models with `x-webhook-root`. */
        val markWebhookRoots: Boolean = false,
    )

    fun process(content: String): String = process(content, Options())

    fun process(content: String, options: Options): String {
        @Suppress("UNCHECKED_CAST")
        val json = JsonSlurper().parseText(content) as? MutableMap<String, Any>
            ?: return content

        if (options.downgradeOpenApiVersion) {
            json["openapi"] = LEGACY_OPENAPI_VERSION
        }
        useMethodNamesAsOperationIds(json)
        options.generalTagReplacement?.let { renameGeneralTag(json, it) }
        if (options.markWebhookRoots) {
            markWebhookRoots(json)
        }

        return JsonOutput.prettyPrint(JsonOutput.toJson(json))
    }

    @Suppress("UNCHECKED_CAST")
    private fun operations(json: Map<String, Any>): List<MutableMap<String, Any>> =
        // Webhooks and notifications do not have 'paths'
        (json["paths"] as? Map<String, Any>)?.values.orEmpty()
            .flatMap { endpoint -> (endpoint as? Map<*, *>)?.values.orEmpty() }
            .mapNotNull { it as? MutableMap<String, Any> }

    private fun useMethodNamesAsOperationIds(json: Map<String, Any>) {
        operations(json).forEach { operation ->
            operation["x-methodName"]?.let { operation["operationId"] = it }
        }
    }

    // A small service has a single 'General' tag; renaming it makes generators name the
    // service file after the API (e.g. BinLookup) instead of 'General'.
    private fun renameGeneralTag(json: Map<String, Any>, replacement: String) {
        operations(json).forEach { operation ->
            val tags = operation["tags"] as? List<*> ?: return@forEach
            operation["tags"] = tags.map { if (it == "General") replacement else it }
        }
    }

    // 'x-webhook-root' marks the model that represents a webhook payload so that templates can
    // generate the handler that deserialises it.
    @Suppress("UNCHECKED_CAST")
    private fun markWebhookRoots(json: Map<String, Any>) {
        val components = json["components"] as? Map<String, Any> ?: return
        val schemas = components["schemas"] as? Map<String, Any> ?: return
        var addOnce = true
        schemas.forEach { (schemaKey, schemaValue) ->
            val schemaDetails = schemaValue as MutableMap<String, Any>
            val properties = schemaDetails["properties"] as Map<String, Any>?
            // the standard webhook model has 'environment' and 'data' attributes
            if (properties?.containsKey("environment") == true && properties.containsKey("data")) {
                schemaDetails["x-webhook-root"] = true
            }
            // bespoke models that do not adopt the standard schema
            if (schemaKey in NON_STANDARD_WEBHOOK_ROOTS) {
                schemaDetails["x-webhook-root"] = true
            }
            // Templates cannot detect "any model is a webhook root" with {{#first}} across several
            // x-webhook-root models, so one model carries this marker instead.
            if (addOnce) {
                schemaDetails["x-has-at-least-one-webhook-root"] = true
                addOnce = false
            }
        }
    }

    private val NON_STANDARD_WEBHOOK_ROOTS = setOf(
        "RelayedAuthenticationRequest", // missing 'environment' and 'data'
        "DisputeNotificationRequest", // missing 'environment'
        "RelayedAuthorisationRequest", // missing 'data'
    )
}
