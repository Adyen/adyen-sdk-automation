package com.adyen.sdk

import groovy.json.JsonOutput
import groovy.json.JsonSlurper

object SpecProcessor {
    fun process(content: String): String {
        @Suppress("UNCHECKED_CAST")
        val json = JsonSlurper().parseText(content) as? MutableMap<String, Any>
            ?: return content

        // Modify the 'openapi' field
        json["openapi"] = "3.0.0"

        @Suppress("UNCHECKED_CAST")
        val paths = json["paths"] as? Map<String, Any>
        // Webhooks and notifications do not have 'paths', so we skip them
        paths?.values?.forEach { endpoint ->
            (endpoint as? Map<*, *>)?.values?.forEach { httpMethod ->
                @Suppress("UNCHECKED_CAST")
                (httpMethod as? MutableMap<String, Any>)?.let { methodDetails ->
                    methodDetails["x-methodName"]?.let {
                        methodDetails["operationId"] = it
                    }
                }
            }
        }

        sanitizeDescriptions(json)

        return JsonOutput.prettyPrint(JsonOutput.toJson(json))
    }

    private fun sanitizeDescriptions(node: Any?) {
        when (node) {
            is MutableMap<*, *> -> {
                @Suppress("UNCHECKED_CAST")
                val map = node as MutableMap<Any?, Any?>
                map.entries.forEach { entry ->
                    if (entry.key == "description" && entry.value is String) {
                        entry.setValue(sanitizeDescription(entry.value as String))
                    } else {
                        sanitizeDescriptions(entry.value)
                    }
                }
            }
            is MutableList<*> -> node.forEach(::sanitizeDescriptions)
        }
    }

    private fun sanitizeDescription(description: String): String =
        description
            // Only fix escaped closing parentheses that appear at the end of a markdown link URL,
            // e.g. `[text](url\)`. A global `\)` -> `)` replacement would corrupt legitimate
            // escaped parentheses in code snippets or regular expressions.
            .replace(Regex("""(\[[^\]]*\]\([^)]*)\\\)""")) { match ->
                match.groupValues[1] + ")"
            }
            .lines()
            .joinToString("\n") { it.trimEnd() }
            .trimEnd()
}
