package com.adyen.sdk

import org.openapitools.codegen.languages.RubyClientCodegen

/**
 * Ruby client generator with Adyen-specific Mustache lambdas on top of the
 * stock Ruby generator. Referenced by its fully-qualified class name as the
 * `generatorName` of the Ruby generate tasks.
 */
class AdyenRubyCodegen : RubyClientCodegen() {
    override fun processOpts() {
        super.processOpts()
        additionalProperties["lambda.escapeSingleQuotedString"] = EscapeSingleQuotedStringLambda()
    }
}
