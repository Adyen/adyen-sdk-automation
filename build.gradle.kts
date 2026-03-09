import groovy.json.JsonOutput
import groovy.json.JsonSlurper

val uri = "https://github.com/Adyen/adyen-openapi.git"
val specsDir = "$projectDir/schema"
val checkoutDir = "$projectDir/schema/json/CheckoutService-v71.json"

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
                @Suppress("UNCHECKED_CAST")
                val json = JsonSlurper().parseText(specFile.readText()) as MutableMap<String, Any>
                // Modify the 'openapi' field
                json["openapi"] = "3.0.0"

                @Suppress("UNCHECKED_CAST")
                val paths = json["paths"] as Map<String, Any>
                paths.forEach { (_, endpoint) ->
                    @Suppress("UNCHECKED_CAST")
                    val methods = endpoint as Map<String, Any>
                    methods.forEach { (_, httpMethod) ->
                        @Suppress("UNCHECKED_CAST")
                        val methodDetails = httpMethod as MutableMap<String, Any>
                        // overwrite operationId
                        methodDetails["operationId"] = methodDetails["x-methodName"]!!
                    }
                }

                // Overwrite the file with updated content
                specFile.writeText(JsonOutput.prettyPrint(JsonOutput.toJson(json)))
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
        @Suppress("UNCHECKED_CAST")
        val json = JsonSlurper().parseText(checkoutFile.readText()) as Map<String, Any>
        @Suppress("UNCHECKED_CAST")
        val components = json["components"] as Map<String, Any>
        @Suppress("UNCHECKED_CAST")
        val base = components["schemas"] as Map<String, Any>
        val pmList = mutableMapOf<String, MutableList<String>>()

        // find list of PaymentMethod Classes
        @Suppress("UNCHECKED_CAST")
        val paymentRequest = base["PaymentRequest"] as Map<String, Any>
        @Suppress("UNCHECKED_CAST")
        val properties = paymentRequest["properties"] as Map<String, Any>
        @Suppress("UNCHECKED_CAST")
        val paymentMethod = properties["paymentMethod"] as Map<String, Any>
        @Suppress("UNCHECKED_CAST")
        val oneOf = paymentMethod["oneOf"] as List<Map<String, String>>

        oneOf.forEach { pmClass ->
            val ref = pmClass["\$ref"]!!
            pmList[ref.replace("#/components/schemas/", "")] = mutableListOf()
        }

        // populate available tx variants per PaymentMethodDetailsClass
        pmList.forEach { (keyString, list) ->
            @Suppress("UNCHECKED_CAST")
            val schema = base[keyString] as Map<String, Any>
            @Suppress("UNCHECKED_CAST")
            val schemaProperties = schema["properties"] as Map<String, Any>
            @Suppress("UNCHECKED_CAST")
            val type = schemaProperties["type"] as Map<String, Any>
            @Suppress("UNCHECKED_CAST")
            val enumValues = type["enum"] as List<String>
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
