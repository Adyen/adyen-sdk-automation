package com.adyen.sdk

import com.samskivert.mustache.Mustache
import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test

class EscapeSingleQuotedStringLambdaTest {

    private fun render(message: String): String {
        // inner must be triple-braced (raw), otherwise jmustache HTML-escapes
        // the content before the lambda sees it
        val template = Mustache.compiler()
            .compile("{{#lambda.escapeSingleQuotedString}}{{{message}}}{{/lambda.escapeSingleQuotedString}}")
        val context = mapOf(
            "lambda.escapeSingleQuotedString" to EscapeSingleQuotedStringLambda(),
            "message" to message
        )
        return template.execute(context)
    }

    @Test
    fun `escapes single quotes`() {
        assertThat(render("Use Adyen's API instead."))
            .isEqualTo("Use Adyen\\'s API instead.")
    }

    @Test
    fun `escapes backslashes`() {
        assertThat(render("C:\\temp")).isEqualTo("C:\\\\temp")
    }

    @Test
    fun `escapes a backslash before an already-escaped quote`() {
        // input is backslash + quote (2 chars); the backslash rule runs first,
        // so the result round-trips to the original value in Ruby
        assertThat(render("a\\'b")).isEqualTo("a\\\\\\'b")
    }

    @Test
    fun `leaves double quotes and interpolation sequences untouched`() {
        // inert in single-quoted literals: " needs no escape, #{...} is not interpolated
        assertThat(render("Use \"payments\" #{here} instead."))
            .isEqualTo("Use \"payments\" #{here} instead.")
    }

    @Test
    fun `leaves line breaks untouched`() {
        // legal in single-quoted literals; escaping to \n would corrupt the value
        assertThat(render("first\nsecond")).isEqualTo("first\nsecond")
    }

    @Test
    fun `leaves markdown and other prose untouched`() {
        val message = "Use the `/grants` endpoint from the [Capital API](https://docs.adyen.com/api-explorer/capital) instead."
        assertThat(render(message)).isEqualTo(message)
    }
}
