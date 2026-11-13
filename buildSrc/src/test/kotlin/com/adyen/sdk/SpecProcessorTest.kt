package com.adyen.sdk

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test

class SpecProcessorTest {

    @Test
    fun `replaces openapi version and operationId`() {
        val input = """
            {
              "openapi": "3.1.0",
              "paths": {
                "/test": {
                  "post": {
                    "operationId": "post-test",
                    "x-methodName": "myCustomMethod"
                  }
                }
              }
            }
        """.trimIndent()

        val result = SpecProcessor.process(input)

        assertThat(result).contains("\"openapi\": \"3.0.0\"")
        assertThat(result).contains("\"operationId\": \"myCustomMethod\"")
    }

    @Test
    fun `handles specs without paths`() {
        val input = """
            {
              "openapi": "3.1.0",
              "info": {
                "title": "Webhook"
              }
            }
        """.trimIndent()

        val result = SpecProcessor.process(input)

        assertThat(result).contains("\"openapi\": \"3.0.0\"")
        assertThat(result).contains("\"title\": \"Webhook\"")
    }

    @Test
    fun `handles invalid or empty JSON`() {
        val input = "[]"
        val result = SpecProcessor.process(input)
        assertThat(result).isEqualTo(input)
    }

    @Test
    fun `handles x-methodName absence`() {
        val input = """
            {
              "openapi": "3.1.0",
              "paths": {
                "/test": {
                  "post": {
                    "operationId": "post-test"
                  }
                }
              }
            }
        """.trimIndent()

        val result = SpecProcessor.process(input)

        assertThat(result).contains("\"openapi\": \"3.0.0\"")
        assertThat(result).contains("\"operationId\": \"post-test\"")
    }

    @Test
    fun `preserves the source openapi version and 3_1 constructs when asked`() {
        val input = """
            {
              "openapi": "3.1.0",
              "components": {
                "schemas": {
                  "Amount": {
                    "properties": {
                      "currency": { "type": ["string", "null"] },
                      "value": { "oneOf": [ { "type": "integer" }, { "type": "null" } ] }
                    }
                  }
                }
              }
            }
        """.trimIndent()

        val result = SpecProcessor.process(input, SpecProcessor.Options(downgradeOpenApiVersion = false))

        assertThat(result).contains("\"openapi\": \"3.1.0\"")
        assertThat(result).containsSubsequence("\"type\": [", "\"string\"", "\"null\"")
        assertThat(result).contains("\"type\": \"null\"")
    }

    @Test
    fun `keeps x-methodName as operationId when preserving the version`() {
        val input = """
            { "openapi": "3.1.0", "paths": { "/t": { "get": { "operationId": "get-t", "x-methodName": "getT" } } } }
        """.trimIndent()

        val result = SpecProcessor.process(input, SpecProcessor.Options(downgradeOpenApiVersion = false))

        assertThat(result).contains("\"operationId\": \"getT\"")
    }

    @Test
    fun `renames the General tag only when a replacement is given`() {
        val input = """
            { "openapi": "3.1.0", "paths": { "/t": { "post": { "tags": ["General", "Other"] } } } }
        """.trimIndent()

        val renamed = SpecProcessor.process(input, SpecProcessor.Options(generalTagReplacement = "BinLookup"))
        val untouched = SpecProcessor.process(input)

        assertThat(renamed).containsSubsequence("\"BinLookup\"", "\"Other\"").doesNotContain("\"General\"")
        assertThat(untouched).contains("\"General\"")
    }

    @Test
    fun `marks webhook roots only when asked`() {
        val input = """
            {
              "openapi": "3.1.0",
              "components": {
                "schemas": {
                  "Amount": { "properties": { "value": { "type": "integer" } } },
                  "BalanceWebhook": { "properties": { "environment": {}, "data": {} } },
                  "DisputeNotificationRequest": { "properties": { "data": {} } },
                  "Plain": { "properties": { "data": {} } }
                }
              }
            }
        """.trimIndent()

        @Suppress("UNCHECKED_CAST")
        val schemas = (groovy.json.JsonSlurper().parseText(
            SpecProcessor.process(input, SpecProcessor.Options(markWebhookRoots = true))
        ) as Map<String, Map<String, Map<String, Map<String, Any>>>>)["components"]!!["schemas"]!!

        assertThat(schemas["Amount"]).containsEntry("x-has-at-least-one-webhook-root", true)
            .doesNotContainKey("x-webhook-root")
        assertThat(schemas["BalanceWebhook"]).containsEntry("x-webhook-root", true)
        assertThat(schemas["DisputeNotificationRequest"]).containsEntry("x-webhook-root", true)
        assertThat(schemas["Plain"]).doesNotContainKey("x-webhook-root")
        assertThat(SpecProcessor.process(input)).doesNotContain("x-webhook-root")
    }
    @Test
    fun `normalizes legacy nullable and additionalProperties false for 3_1 generation`() {
        val input = """
            {
              "openapi": "3.1.0",
              "components": {
                "schemas": {
                  "Amount": { "type": "object", "additionalProperties": false, "properties": { "value": { "type": "integer" } } },
                  "Model": {
                    "type": "object",
                    "additionalProperties": false,
                    "properties": {
                      "flag": { "type": "boolean", "nullable": true },
                      "tags": { "type": "array", "items": { "type": "string" }, "nullable": true },
                      "union": { "type": ["string", "null"], "nullable": true },
                      "plain": { "type": "string", "nullable": false },
                      "legacyRef": { "${'$'}ref": "#/components/schemas/Amount", "nullable": true, "description": "kept" },
                      "unionRef": { "oneOf": [ { "${'$'}ref": "#/components/schemas/Amount" }, { "type": "null" } ] },
                      "amount": { "${'$'}ref": "#/components/schemas/Amount" },
                      "map": { "type": "object", "additionalProperties": { "type": "string" } }
                    },
                    "example": { "nullable": true, "additionalProperties": false }
                  }
                }
              }
            }
        """.trimIndent()

        @Suppress("UNCHECKED_CAST")
        val schemas = (groovy.json.JsonSlurper().parseText(
            SpecProcessor.process(input, SpecProcessor.Options(downgradeOpenApiVersion = false, normalizeForOpenApi31 = true))
        ) as Map<String, Map<String, Map<String, Map<String, Any?>>>>)["components"]!!["schemas"]!!
        val model = schemas["Model"]!!
        @Suppress("UNCHECKED_CAST")
        val props = model["properties"] as Map<String, Map<String, Any?>>
        val marker = mapOf("${'$'}ref" to "#/components/schemas/Amount", SpecProcessor.NULLABLE_REF_MARKER to true)

        assertThat(model).doesNotContainKey("additionalProperties")
        assertThat(schemas["Amount"]).doesNotContainKey("additionalProperties")
        assertThat(props["flag"]).isEqualTo(mapOf("type" to listOf("boolean", "null")))
        assertThat(props["tags"]).containsEntry("type", listOf("array", "null")).doesNotContainKey("nullable")
        assertThat(props["union"]).isEqualTo(mapOf("type" to listOf("string", "null")))
        assertThat(props["plain"]).isEqualTo(mapOf("type" to "string"))
        assertThat(props["legacyRef"]).isEqualTo(mapOf("\$ref" to "#/components/schemas/Amount", "description" to "kept"))
        assertThat(props["unionRef"]).isEqualTo(mapOf("oneOf" to listOf(marker, mapOf("type" to "null"))))
        assertThat(props["amount"]).isEqualTo(mapOf("${'$'}ref" to "#/components/schemas/Amount"))
        assertThat(props["map"]).containsEntry("additionalProperties", mapOf("type" to "string"))
        assertThat(model["example"]).isEqualTo(mapOf("nullable" to true, "additionalProperties" to false))
    }

    @Test
    fun `leaves nullable and additionalProperties alone without 3_1 normalization`() {
        val input = """
            { "openapi": "3.1.0", "components": { "schemas": { "M": { "type": "object", "additionalProperties": false,
              "properties": { "f": { "type": "boolean", "nullable": true } } } } } }
        """.trimIndent()

        val result = SpecProcessor.process(input)

        assertThat(result).contains("\"additionalProperties\": false").contains("\"nullable\": true")
    }

    @Test
    fun `names inline enums of array items after their model and property when asked`() {
        val input = """
            { "openapi": "3.1.0", "components": { "schemas": { "PaymentRequest": { "properties": {
              "channels": { "type": "array", "items": { "type": "string", "enum": ["web", "app"] } },
              "titled": { "type": "array", "items": { "type": "string", "enum": ["a"], "title": "Kept" } },
              "refs": { "type": "array", "items": { "${'$'}ref": "#/components/schemas/Channel" } },
              "tags": { "type": "array", "items": { "type": "string" } }
            } } } } }
        """.trimIndent()

        @Suppress("UNCHECKED_CAST")
        val props = ((groovy.json.JsonSlurper().parseText(
            SpecProcessor.process(input, SpecProcessor.Options(nameArrayItemEnums = true))
        ) as Map<String, Map<String, Map<String, Map<String, Any?>>>>)["components"]!!["schemas"]!!["PaymentRequest"]!!["properties"]
            as Map<String, Map<String, Map<String, Any?>>>)

        assertThat(props["channels"]!!["items"]).containsEntry("title", "PaymentRequest_channels")
        assertThat(props["titled"]!!["items"]).containsEntry("title", "Kept")
        assertThat(props["refs"]!!["items"]).doesNotContainKey("title")
        assertThat(props["tags"]!!["items"]).doesNotContainKey("title")
        assertThat(SpecProcessor.process(input)).doesNotContain("PaymentRequest_channels")
    }

    @Test
    fun `uses enum values as variable names when asked`() {
        val input = """
            { "openapi": "3.1.0", "components": { "schemas": {
              "Status": { "type": "string", "enum": ["active", "", "ONECLICK,RECURRING"] },
              "Code": { "type": "integer", "enum": [1, 2] },
              "Named": { "type": "string", "enum": ["a"], "x-enum-varnames": ["Custom"] },
              "Model": { "properties": { "kind": { "type": "string", "enum": ["card"] } },
                "example": { "enum": ["x"] } }
            } } }
        """.trimIndent()

        @Suppress("UNCHECKED_CAST")
        val schemas = (groovy.json.JsonSlurper().parseText(
            SpecProcessor.process(input, SpecProcessor.Options(enumValuesAsVarNames = true))
        ) as Map<String, Map<String, Map<String, Map<String, Any?>>>>)["components"]!!["schemas"]!!
        @Suppress("UNCHECKED_CAST")
        val kind = (schemas["Model"]!!["properties"] as Map<String, Map<String, Any?>>)["kind"]!!

        assertThat(schemas["Status"]).containsEntry("x-enum-varnames", listOf("active", "Empty", "ONECLICK,RECURRING"))
        assertThat(schemas["Code"]).containsEntry("x-enum-varnames", listOf("1", "2"))
        assertThat(schemas["Named"]).containsEntry("x-enum-varnames", listOf("Custom"))
        assertThat(kind).containsEntry("x-enum-varnames", listOf("card"))
        assertThat(schemas["Model"]!!["example"]).isEqualTo(mapOf("enum" to listOf("x")))
        assertThat(SpecProcessor.process(input)).doesNotContain("\"Empty\"")
    }
}
