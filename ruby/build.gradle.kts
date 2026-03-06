import com.adyen.sdk.Service
import com.adyen.sdk.SdkAutomationExtension
import org.openapitools.generator.gradle.plugin.tasks.GenerateTask

plugins {
    id("adyen.sdk-automation-conventions")
}

val sdkAutomation = extensions.getByType<SdkAutomationExtension>()
sdkAutomation.generator.set("ruby")

val services = sdkAutomation.services.get()
val serviceNaming = sdkAutomation.serviceNamingCamel.get()

services.forEach { svc ->
    val serviceName = serviceNaming[svc.id]!!

    // Generation
    tasks.named<GenerateTask>("generate${svc.name}") {
        configFile.set("$projectDir/config.yaml")

        additionalProperties.putAll(mapOf(
            "serviceName" to serviceName
        ))
        // skip generation of models, docs, tests
        globalProperties.putAll(mapOf(
            "apis" to "",
            "supportingFiles" to ""
        ))

        // when generating Classic Payment add prefix for service classes
        if (serviceName == "payment") {
            additionalProperties.put("classicPrefix", "Classic")
        }
    }

    // Copy services
    val deployServices = tasks.register<Sync>("deploy${svc.name}Services") {
        group = "deploy"
        description = "Deploy ${svc.name} into the repo."
        dependsOn("generate${svc.name}")
        outputs.upToDateWhen { false }
        onlyIf { !svc.isWebhook }

        // delete existing services
        doFirst {
            delete(layout.projectDirectory.dir("repo/lib/adyen/services/$serviceName"))
        }

        // rename and copy generated services (i.e. bin_lookup_api.rb)
        from(layout.buildDirectory.dir("services/${svc.id}/lib/openapi_client/api"))
        include("*_api.rb")
        into(layout.projectDirectory.dir("repo/lib/adyen/services/$serviceName"))

        // rename and copy generated service facades (i.e. binLookup.rb)
        from(layout.buildDirectory.dir("services/${svc.id}/api")) {
            include("api-single.rb")
            rename("api-single.rb", "$serviceName.rb")
            into("..")
        }
    }

    tasks.named(svc.id) {
        dependsOn(deployServices)
    }
}

// Tests
tasks.named("checkout") {
    doLast {
        assert(file("${layout.projectDirectory}/repo/lib/adyen/services/checkout/payments_api.rb").exists())
        assert(file("${layout.projectDirectory}/repo/lib/adyen/services/checkout.rb").exists())
    }
}
tasks.named("binlookup") {
    doLast {
        assert(file("${layout.projectDirectory}/repo/lib/adyen/services/binLookup/bin_lookup_api.rb").exists())
        assert(file("${layout.projectDirectory}/repo/lib/adyen/services/binLookup").exists())
    }
}
