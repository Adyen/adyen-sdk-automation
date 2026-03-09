package com.adyen.sdk

import kotlinx.serialization.json.*

/**
 * Utility for performing "Safe Patching" on JSON documents.
 *
 * ### Why use Safe Patching?
 * When working with large, complex JSON schemas like OpenAPI, we often only care about
 * a small subset of fields (e.g., `openapi` version, `operationId`, or custom `x-` extensions).
 *
 * If we were to decode the entire document into a strictly-typed Data Class, any fields
 * not defined in that class would be lost during re-encoding (deserialization -> serialization).
 *
 * ### Benefits:
 * 1. **Data Preservation**: Fields not mapped in our `@Serializable` models (unknown fields)
 *    remain untouched in the original [JsonObject].
 * 2. **Strong Typing**: We can use typed models for the fields we *do* care about, gaining
 *    compiler checks and IDE autocomplete.
 * 3. **Minimal Patches**: Our `patchJson` is configured to not encode defaults or nulls,
 *    ensuring that only the fields we explicitly modified are merged back.
 *
 * ### Example:
 * Original JSON: `{"openapi": "3.1.0", "info": {"title": "API"}, "paths": {...}}`
 * Typed Model (Partial): `data class Spec(val openapi: String)`
 *
 * If we modify `openapi` to "3.0.0" and use [patch]:
 * 1. Decode: We get `Spec(openapi="3.1.0")`. `info` and `paths` are ignored but held in the 'root' JsonObject.
 * 2. Modify: `spec.copy(openapi="3.0.0")`.
 * 3. Patch: The utility merges the new `openapi` value back into the 'root'.
 * 4. Result: `{"openapi": "3.0.0", "info": {"title": "API"}, "paths": {...}}`
 *    *(Note how 'info' and 'paths' were preserved even though the Typed Model didn't know about them)*.
 */
object JsonUtils {
    /**
     * Recursively merges [patch] into [this] JsonElement.
     * If [patch] has a field with a non-null value, it overwrites the value in [this].
     * If both are JsonObjects, they are merged recursively.
     */
    fun JsonElement.patch(patch: JsonElement): JsonElement {
        if (this !is JsonObject || patch !is JsonObject) return patch
        
        val result = this.toMutableMap()
        patch.forEach { (key, value) ->
            val existing = result[key]
            if (existing != null) {
                result[key] = existing.patch(value)
            } else {
                result[key] = value
            }
        }
        return JsonObject(result)
    }

    /**
     * A Json instance configured for partial updates.
     * It ignores unknown keys when reading and does not encode nulls or defaults
     * to ensure our patches only contain the fields we've explicitly set.
     */
    val patchJson = Json {
        ignoreUnknownKeys = true
        encodeDefaults = false
    }
}
