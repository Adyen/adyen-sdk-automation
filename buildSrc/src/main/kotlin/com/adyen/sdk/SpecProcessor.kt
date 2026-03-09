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

        return JsonOutput.prettyPrint(JsonOutput.toJson(json))
    }
}
