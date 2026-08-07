package com.adyen.sdk

import com.samskivert.mustache.Mustache
import com.samskivert.mustache.Template
import java.io.Writer

/**
 * Mustache lambda that escapes its rendered content for inclusion in a Ruby
 * single-quoted string literal.
 *
 * Usage in templates: {{#lambda.escapeSingleQuotedString}}...{{/lambda.escapeSingleQuotedString}}
 *
 * Unlike Mustache's built-in {{.}} escaping (which targets HTML and would turn
 * e.g. backticks into &#x60;), this escapes only what Ruby single-quoted syntax
 * recognizes: backslashes and single quotes.
 */
class EscapeSingleQuotedStringLambda : Mustache.Lambda {
    override fun execute(fragment: Template.Fragment, writer: Writer) {
        val escaped = fragment.execute()
            // Backslash first: it doubles only pre-existing backslashes, so the
            // quote escape introduced below is never re-processed.
            .replace("\\", "\\\\")
            .replace("'", "\\'")
        writer.write(escaped)
    }
}
