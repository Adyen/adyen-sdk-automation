package com.adyen.sdk

import org.gradle.api.provider.ListProperty
import org.gradle.api.provider.MapProperty
import org.gradle.api.provider.Property

interface SdkAutomationExtension {
    /**
     * The target generator name (e.g., "java", "typescript", "python", etc.)
     */
    val generator: Property<String>

    /**
     * The templates directory relative to the repository root
     */
    val templates: Property<String>

    /**
     * The current service name being processed
     */
    val serviceName: Property<String>

    /**
     * Whether to remove tags during generation
     */
    val removeTags: Property<Boolean>

    /**
     * List of all services to be generated
     */
    val services: ListProperty<Service>

    /**
     * List of small services
     */
    val smallServices: ListProperty<Service>

    /**
     * Map of service ID to service name
     */
    val serviceNaming: MapProperty<String, String>

    /**
     * Map of service ID to service name (camelCase)
     */
    val serviceNamingCamel: MapProperty<String, String>

    /**
     * The OpenAPI generator version
     */
    val openApiVersion: Property<String>
}
