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
        /** Rewrite 3.0-only constructs (`nullable`, `additionalProperties: false`) for native 3.1 generation. */
        val normalizeForOpenApi31: Boolean = false,
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
        if (options.normalizeForOpenApi31) {
            normalizeForOpenApi31(json)
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

    /** Rewrites 3.0-only constructs so that OpenAPI Generator reads the spec as native 3.1. */
    @Suppress("UNCHECKED_CAST")
    private fun normalizeForOpenApi31(node: Any?) {
        when (node) {
            is MutableMap<*, *> -> {
                val schema = node as MutableMap<String, Any?>
                // Generator 7.11 parses `additionalProperties: false` in 3.1 as a schema: models are then
                // treated as maps, their properties skip 3.1 normalization (nullable unions are lost) and
                // gain an AdditionalProperties field. Absent means "not allowed" with the generator default
                // disallowAdditionalPropertiesIfNotPresent=true, so dropping it keeps the meaning.
                if (schema["additionalProperties"] == false) {
                    schema.remove("additionalProperties")
                }
                when (schema["nullable"]) {
                    true -> rewriteLegacyNullable(schema)
                    false -> schema.remove("nullable")
                }
                markNullableRefMembers(schema)
                // Examples are payloads, not schemas.
                schema.filterKeys { it != "example" && it != "examples" }.values.forEach { normalizeForOpenApi31(it) }
            }
            is List<*> -> node.forEach { normalizeForOpenApi31(it) }
        }
    }

    // The 3.1 parser shares one schema instance between identical `{"$ref": ...}` nodes, and the
    // generator marks that instance nullable when it collapses `oneOf: [$ref, null]`. Without a
    // distinguishing key every plain reference to the same model would become nullable too.
    @Suppress("UNCHECKED_CAST")
    private fun markNullableRefMembers(schema: Map<String, Any?>) {
        listOf("oneOf", "anyOf").forEach { key ->
            val members = schema[key] as? List<*> ?: return@forEach
            if (members.none { (it as? Map<*, *>)?.get("type") == "null" }) return@forEach
            members.forEach { member ->
                val ref = member as? MutableMap<String, Any?> ?: return@forEach
                if (ref.containsKey("\$ref")) ref[NULLABLE_REF_MARKER] = true
            }
        }
    }

    // `nullable` is not an OpenAPI 3.1 keyword, so 3.1 parsers ignore it.
    @Suppress("UNCHECKED_CAST")
    private fun rewriteLegacyNullable(schema: MutableMap<String, Any?>) {
        val ref = schema["\$ref"]
        val type = schema["type"]
        val oneOf = schema["oneOf"] as? MutableList<Any?>
        when {
            ref != null -> {
                schema.remove("\$ref")
                schema["oneOf"] = mutableListOf(mutableMapOf("\$ref" to ref), mutableMapOf("type" to "null"))
            }
            type is String -> schema["type"] = mutableListOf(type, "null")
            type is List<*> -> if ("null" !in type) schema["type"] = type + "null"
            oneOf != null -> if (oneOf.none { (it as? Map<*, *>)?.get("type") == "null" }) oneOf.add(mutableMapOf("type" to "null"))
            else -> return
        }
        schema.remove("nullable")
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

    const val NULLABLE_REF_MARKER = "x-adyen-nullable-ref"

    private val NON_STANDARD_WEBHOOK_ROOTS = setOf(
        "RelayedAuthenticationRequest", // missing 'environment' and 'data'
        "DisputeNotificationRequest", // missing 'environment'
        "RelayedAuthorisationRequest", // missing 'data'
    )
}
