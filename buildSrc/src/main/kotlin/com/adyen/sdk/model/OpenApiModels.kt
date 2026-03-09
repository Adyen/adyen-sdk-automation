package com.adyen.sdk.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class OpenApiSpec(
    val openapi: String? = null,
    val paths: Map<String, PathItem>? = null,
    val components: Components? = null
)

@Serializable
data class PathItem(
    val get: Operation? = null,
    val post: Operation? = null,
    val put: Operation? = null,
    val delete: Operation? = null,
    val patch: Operation? = null
) {
    fun operations(): Map<String, Operation> = mapOf(
        "get" to get,
        "post" to post,
        "put" to put,
        "delete" to delete,
        "patch" to patch
    ).filterValues { it != null } as Map<String, Operation>
}

@Serializable
data class Operation(
    val operationId: String? = null,
    val tags: List<String>? = null,
    @SerialName("x-methodName") val xMethodName: String? = null
)

@Serializable
data class Components(
    val schemas: Map<String, Schema>? = null
)

@Serializable
data class Schema(
    val type: String? = null,
    val properties: Map<String, Schema>? = null,
    val oneOf: List<Schema>? = null,
    val enum: List<String>? = null,
    @SerialName("\$ref") val ref: String? = null,
    @SerialName("x-webhook-root") val xWebhookRoot: Boolean? = null,
    @SerialName("x-has-at-least-one-webhook-root") val xHasAtLeastOneWebhookRoot: Boolean? = null
)
