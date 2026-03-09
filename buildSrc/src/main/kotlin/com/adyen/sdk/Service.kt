package com.adyen.sdk

/**
 * Holds required information for code generation.
 */
data class Service(
    /**
     * The target name of the generated service
     */
    val name: String,

    /**
     * The source API spec
     */
    val spec: String? = null,

    /**
     * The version of the source API spec
     */
    val version: Int,

    /**
     * A "small" service is a service that is generated in a self-contained file.
     * In contrast, for some languages, the generated code might be bundled inside a directory.
     * Note that it's up to the underlying libs to honor this flag.
     */
    /*
      TODO: review where this is actually used because it **feels** lib specific and
        not generic enough to deserve its place here.
        Plus, "small" doesn't hint much about its actual meaning.
     */
    var small: Boolean = false
) {
    val id: String get() = name.lowercase()

    /**
     * The target file associated with this service
     *
     * @return The file name associated with this service
     */
    val filename: String get() = "${getSpecName()}-v$version.json"

    /**
     * Indicates whether this target is related to a spec from a webhook.
     *
     * @return <code>true</code> if this service is a webhook
     */
    val isWebhook: Boolean get() = name.endsWith("Webhooks")

    /**
     * The spec convention name.
     * If this service has no explicit spec, it defaults to `<name>Service`
     *
     * @return The spec convention name
     */
    fun getSpecName(): String = spec ?: "${name}Service"
}
