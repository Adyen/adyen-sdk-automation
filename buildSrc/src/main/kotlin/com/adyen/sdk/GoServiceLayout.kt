package com.adyen.sdk

/**
 * Where and how one catalog service is generated in the Go library.
 *
 * Every Go service derives its settings here, so that options set for one service cannot leak
 * into another one.
 */
data class GoServiceLayout(
    /** Go package name; also the directory under `src/`. */
    val packageName: String,
    /** `serviceName` template value; selects the `<serviceName>Endpoint` config field. */
    val serviceName: String,
    /** Webhook packages contain models only; their `client.go` is never deployed. */
    val isWebhook: Boolean,
    /** Catalog `small` flag: the service is expected to have a single `General` tag. */
    val small: Boolean,
    /** Handwritten files that deployment must keep in the target directory. */
    val preservedFiles: Set<String>,
) {
    val directory: String get() = "src/$packageName"

    /**
     * Whether the generated `client.go` is deployed, given the names of the generated files.
     *
     * A small service is used through its single API type, so it needs no `APIClient`. A small
     * service whose spec has several tags (Payment) still needs the `APIClient` grouping them.
     */
    fun deploysClient(generatedFiles: Collection<String>): Boolean =
        !isWebhook && (!small || generatedFiles.count { it.startsWith("api_") && it.endsWith(".go") } > 1)

    companion object {
        // Names that predate the catalog conventions and are part of the public import paths.
        private val LEGACY = mapOf(
            "Payment" to Override(packageName = "payments", serviceName = ""),
            "Payout" to Override(serviceName = ""),
            "LegalEntityManagement" to Override(packageName = "legalentity", serviceName = "LegalEntity"),
        )

        const val WEBHOOK_HANDLER = "webhook_handler.go"

        fun of(service: Service): GoServiceLayout {
            val override = LEGACY[service.name]
            // Webhook packages are singular, e.g. AcsWebhooks -> acswebhook.
            val defaultPackage = if (service.isWebhook) service.id.removeSuffix("s") else service.id
            return GoServiceLayout(
                packageName = override?.packageName ?: defaultPackage,
                serviceName = override?.serviceName ?: service.name,
                isWebhook = service.isWebhook,
                small = service.small,
                preservedFiles = if (service.isWebhook) setOf(WEBHOOK_HANDLER) else emptySet(),
            )
        }
    }

    private data class Override(val packageName: String? = null, val serviceName: String? = null)
}
