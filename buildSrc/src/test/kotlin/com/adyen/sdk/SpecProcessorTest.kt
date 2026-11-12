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
    }}
