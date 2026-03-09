plugins {
    kotlin("plugin.serialization") version "2.3.0"
}

import kotlinx.serialization.json.*
import com.adyen.sdk.model.*
import com.adyen.sdk.JsonUtils.patchJson

val uri = "https://github.com/Adyen/adyen-openapi.git"
val specsDir = "$projectDir/schema"
val checkoutDir = "$projectDir/schema/json/CheckoutService-v71.json"

buildscript {
    repositories {
        mavenCentral()
    }
    dependencies {
        classpath("org.jetbrains.kotlinx:kotlinx-serialization-json:1.10.0")
    }
}

tasks.register<Exec>("specs") {
    group = "setup"
    description = "Clone OpenAPI spec (and apply local patches)."
    commandLine("git", "clone", "--depth", "2", uri, specsDir)
    outputs.dir(specsDir)
    onlyIf { !file(specsDir).exists() }
    doLast {
        val folder = File("$specsDir/json")
        assert(folder.exists())
        assert(folder.isDirectory)
        assert(folder.list()?.isNotEmpty() ?: false) { "Folder cannot be empty after clone" }
        file(folder).walkTopDown().maxDepth(1).forEach { specFile ->
            if (specFile.name.endsWith(".json")) {
                specFile.writeText(com.adyen.sdk.SpecProcessor.process(specFile.readText()))
            }
        }
    }
}

tasks.register("pmTable") {
    group = "specs"
    description = "Generate Checkout Payment Method Table"
    dependsOn("specs")
    val checkoutFile = file(checkoutDir)
    onlyIf { checkoutFile.exists() }
    doLast {
        val root = Json.parseToJsonElement(checkoutFile.readText()).jsonObject
        val spec = patchJson.decodeFromJsonElement<OpenApiSpec>(root)
        val schemas = spec.components?.schemas ?: return@doLast
        val pmList = mutableMapOf<String, MutableList<String>>()

        // find list of PaymentMethod Classes
        val paymentRequest = schemas["PaymentRequest"] ?: return@doLast
        val paymentMethod = paymentRequest.properties?.get("paymentMethod") ?: return@doLast
        val oneOf = paymentMethod.oneOf ?: return@doLast

        oneOf.forEach { pmClass ->
            val ref = pmClass.ref ?: return@forEach
            pmList[ref.replace("#/components/schemas/", "")] = mutableListOf()
        }

        // populate available tx variants per PaymentMethodDetailsClass
        pmList.forEach { (keyString, list) ->
            val schema = schemas[keyString] ?: return@forEach
            val type = schema.properties?.get("type") ?: return@forEach
            val enumValues = type.enum ?: return@forEach
            list.addAll(enumValues)
        }
        println(pmList)

        // Output the list into a .md file
        val pmFile = file("$projectDir/PaymentMethodOverview.md")
        pmFile.bufferedWriter().use { writer ->
            writer.write("# PaymentMethod Overview For Checkout\n")
            writer.write("| Java Class    | tx_variants   |\n")
            writer.write("|---------------|---------------|\n")
            pmList.forEach { (key, value) ->
                writer.write("|$key|$value|\n")
            }
        }
    }
}

tasks.register<Delete>("cleanSpecs") {
    group = "clean"
    description = "Delete OpenAPI specifications"
    delete(specsDir)
}
