package com.adyen.sdk

import com.adyen.sdk.JsonUtils.patch
import com.adyen.sdk.JsonUtils.patchJson
import com.adyen.sdk.model.*
import kotlinx.serialization.json.*

object SpecProcessor {
    private val jsonFormatter = Json { prettyPrint = true }

    fun process(content: String): String {
        val root = try {
            Json.parseToJsonElement(content).jsonObject
        } catch (e: Exception) {
            return content
        }

        // Decode into typed model (ignores unknown fields)
        val spec = patchJson.decodeFromJsonElement<OpenApiSpec>(root)

        // Modify the typed models
        val modifiedPaths = spec.paths?.mapValues { (_, pathItem) ->
            pathItem.copy(
                get = pathItem.get?.withOperationIdFromMethod(),
                post = pathItem.post?.withOperationIdFromMethod(),
                put = pathItem.put?.withOperationIdFromMethod(),
                delete = pathItem.delete?.withOperationIdFromMethod(),
                patch = pathItem.patch?.withOperationIdFromMethod()
            )
        }

        val modifiedSpec = spec.copy(
            openapi = "3.0.0",
            paths = modifiedPaths
        )

        // Encode back and patch the original root to preserve unknown fields
        val patch = patchJson.encodeToJsonElement(modifiedSpec)
        val finalJson = root.patch(patch)

        return jsonFormatter.encodeToString(JsonElement.serializer(), finalJson)
    }

    private fun Operation.withOperationIdFromMethod(): Operation =
        if (xMethodName != null) this.copy(operationId = xMethodName) else this
}
