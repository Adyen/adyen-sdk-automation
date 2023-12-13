package com.adyen.sdk

class Service {
    String name, spec
    int version
    boolean small

    String getId() { name.toLowerCase() }

    String getSpec() { spec ?: "${name}Service" }

    String getFilename() { "${getSpec()}-v${version}.json" }

    boolean isWebhook() { name.endsWith('Webhooks') }
}