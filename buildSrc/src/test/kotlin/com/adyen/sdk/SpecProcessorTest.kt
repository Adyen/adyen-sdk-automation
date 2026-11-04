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
    fun `sanitizes nested descriptions`() {
        val input = """
            {
              "openapi": "3.1.0",
              "paths": {
                "/test": {
                  "get": {
                    "description": "Operation description.  \n",
                    "parameters": [
                      {
                        "description": "See [ISO 8601](https://example.com\\).  ",
                        "name": "date"
                      },
                      {
                        "description": "Use regex \\) to match a parenthesis.",
                        "name": "regex"
                      }
                    ]
                  }
                }
              },
              "components": {
                "parameters": {
                  "test": {
                    "description": "Component description.  "
                  }
                }
              }
            }
        """.trimIndent()

        val result = SpecProcessor.process(input)

        assertThat(result).contains("\"description\": \"Operation description.\"")
        assertThat(result).contains("\"description\": \"See [ISO 8601](https://example.com).\"")
        assertThat(result).contains("\"description\": \"Component description.\"")
        assertThat(result).contains("\"description\": \"Use regex \\\\) to match a parenthesis.\"")
        assertThat(SpecProcessor.process(result)).isEqualTo(result)
    }
}
