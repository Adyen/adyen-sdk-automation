package com.adyen.sdk

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

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

        assertTrue(result.contains("\"openapi\": \"3.0.0\""))
        assertTrue(result.contains("\"operationId\": \"myCustomMethod\""))
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

        assertTrue(result.contains("\"openapi\": \"3.0.0\""))
        assertTrue(result.contains("\"title\": \"Webhook\""))
    }

    @Test
    fun `handles invalid or empty JSON`() {
        val input = "[]"
        val result = SpecProcessor.process(input)
        assertEquals(input, result)
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

        assertTrue(result.contains("\"openapi\": \"3.0.0\""))
        assertTrue(result.contains("\"operationId\": \"post-test\""))
    }
}
