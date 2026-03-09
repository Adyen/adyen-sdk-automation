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
        paths?.forEach { (_, endpoint) ->
            if (endpoint is Map<*, *>) {
                endpoint.forEach { (method, httpMethod) ->
                    if (httpMethod is MutableMap<*, *>) {
                        @Suppress("UNCHECKED_CAST")
                        val methodDetails = httpMethod as MutableMap<String, Any>
                        // overwrite operationId if x-methodName exists (not all operations have this extension)
                        methodDetails["x-methodName"]?.let {
                            methodDetails["operationId"] = it
                        }
                    }
                }
            }
        }

        return JsonOutput.prettyPrint(JsonOutput.toJson(json))
    }
}
