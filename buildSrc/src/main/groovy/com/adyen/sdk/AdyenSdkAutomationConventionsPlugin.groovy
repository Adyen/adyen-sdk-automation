package com.adyen.sdk

import groovy.json.JsonOutput
import groovy.json.JsonSlurper
import org.gradle.api.Plugin
import org.gradle.api.Project
import org.gradle.api.tasks.Copy
import org.gradle.api.tasks.Delete
import org.gradle.api.tasks.Exec
import org.openapitools.generator.gradle.plugin.tasks.GenerateTask

class AdyenSdkAutomationConventionsPlugin implements Plugin<Project> {
    void apply(Project project) {
        
        project.plugins.apply('org.openapi.generator')

        project.repositories {
            mavenCentral()
        }

        List<Service> services = [
                // Payments
                new Service(name: 'Checkout', version: 71),
                new Service(name: 'Payout', version: 68),
                new Service(name: 'Recurring', version: 68, small: true),
                new Service(name: 'BinLookup', version: 54, small: true),
                new Service(name: 'PosMobile', spec: 'SessionService', version: 68, small: true),
                new Service(name: 'PaymentsApp', spec: 'PaymentsAppService', version: 1, small: true),
                // Management
                new Service(name: 'Management', version: 3),
                new Service(name: 'BalanceControl', version: 1, small: true),
                // Adyen for Platforms
                new Service(name: 'LegalEntityManagement', spec: 'LegalEntityService', version: 3),
                new Service(name: 'BalancePlatform', version: 2),
                new Service(name: 'Transfers', spec: 'TransferService', version: 4),
                new Service(name: 'DataProtection', version: 1, small: true),
                new Service(name: 'SessionAuthentication', version: 1),
                // Classic Payments
                new Service(name: 'Payment', version: 68, small: true),
                // Others
                new Service(name: 'StoredValue', version: 46, small: true),
                new Service(name: 'Disputes', spec: 'DisputeService', version: 30, small: true),
                // Webhooks
                new Service(name: 'ConfigurationWebhooks', spec: 'BalancePlatformConfigurationNotification', version: 2),
                new Service(name: 'AcsWebhooks', spec: 'BalancePlatformAcsNotification', version: 1),
                new Service(name: 'ReportWebhooks', spec: 'BalancePlatformReportNotification', version: 1),
                new Service(name: 'TransferWebhooks', spec: 'BalancePlatformTransferNotification', version: 4),
                new Service(name: 'TransactionWebhooks', spec: 'BalancePlatformTransactionNotification', version: 4),
                new Service(name: 'ManagementWebhooks', spec: 'ManagementNotificationService', version: 3),
                new Service(name: 'DisputeWebhooks', spec: 'BalancePlatformDisputeNotification', version: 1),
                new Service(name: 'NegativeBalanceWarningWebhooks', spec: 'BalancePlatformNegativeBalanceCompensationWarningNotification', version: 1),
                new Service(name: 'BalanceWebhooks', spec: 'BalancePlatformBalanceNotification', version: 1),
                new Service(name: 'TokenizationWebhooks', spec: 'TokenizationNotification', version: 1)
        ]

        project.ext {
            generator = project.name
            templates = 'templates'
            serviceName = ''
            removeTags = true
            setProperty('services', services)
            smallServices = services.findAll { it.small }
            serviceNaming = services.collectEntries { [it.id, it.name] }
            serviceNamingCamel = services.collectEntries {
                [it.id, it.name.substring(0, 1).toLowerCase() + it.name.substring(1)]
            }
        }

        // Generate a full client for each service
        services.each { Service svc ->
            def generate = project.tasks.register("generate$svc.name", GenerateTask) {
                group 'generate'
                description "Generate a $project.name client for $svc.name."
                dependsOn 'cloneRepo'
                dependsOn ':specs'

                // Current service being processed
                ext.serviceId = svc.id
                project.ext.serviceName = svc.name

                generatorName.set(project.ext.generator as String)
                inputSpec.set("$project.rootDir/schema/json/${svc.filename}")
                outputDir.set("$project.buildDir/services/${svc.id}")
                templateDir.set("$project.projectDir/repo/$project.ext.templates")
                engine.set('mustache')
                validateSpec.set(false)
                skipValidateSpec.set(true)
                reservedWordsMappings.set([
                        "configuration": "configuration"
                ])
                additionalProperties.set([
                        'serviceName': project.ext.serviceName,
                ])
                globalProperties.set([
                        'modelDocs' : 'false',
                        'modelTests': 'false'
                ])

                if (project.ext.has('configFile')) {
                    configFile.set("$project.projectDir/repo/$project.ext.configFile")
                }
            }

            project.tasks.register(svc.id) {
                group 'service'
                description "Base task for $svc.name."
                dependsOn generate
            }
        }

        project.tasks.register('services') {
            description 'Generate code for multiple services.'
            dependsOn services.collect { it.id }
        }

        project.tasks.named('generateCheckout', GenerateTask) {
            if (project.name == 'node') {
                // generator v5 does not support inlineSchemaNameMappings
                return
            }
            inlineSchemaNameMappings.set([
                    'PaymentRequest_paymentMethod'        : 'CheckoutPaymentMethod',
                    'DonationPaymentRequest_paymentMethod': 'DonationPaymentMethod',
            ])
        }

        project.tasks.register('cloneRepo', Exec) {
            group 'setup'
            def uri = "https://github.com/Adyen/adyen-$project.name-api-library.git"
            def dest = 'repo'
            description "Clone this project's repository."
            commandLine 'git', 'clone', uri, '--single-branch', dest
            outputs.dir dest
            onlyIf { !project.file(dest).exists() }
        }

        // Disable generator caching
        project.tasks.withType(GenerateTask).configureEach {
            outputs.upToDateWhen { false }
            outputs.cacheIf { false }
        }

        project.tasks.register('cleanRepo', Delete) {
            group 'clean'
            description 'Clean this project state'
            delete project.layout.buildDirectory
            doLast {
                project.exec {
                    // cleanTracked: discard changes to existing files
                    commandLine 'git', 'checkout', '.'
                    workingDir 'repo'
                }
                project.exec {
                    // cleanUntracked: discard unknown files
                    commandLine 'git', 'clean', '-f', '-d'
                    workingDir 'repo'
                }
            }
        }

        project.tasks.register('addPMTable', Copy) {
            dependsOn("cloneRepo")
            dependsOn(":pmTable")
            from(project.rootProject.file('PaymentMethodOverview.md'))
            into project.layout.projectDirectory.dir("repo")
        }

        // update OpenAPI file of the smallService to rename the tag from 'General' to the name of the API (i.e. Binlookup)
        // this is necessary to generate the service/class file using the name of the API (instead of General)
        project.ext.smallServices.each { Service svc ->
            def ungroup = project.tasks.register("ungroup${svc.name}") {
                group 'specs'
                description "Update tags in ${svc.name}"
                dependsOn ':specs'
                onlyIf { project.ext.removeTags }
                doLast {
                    def specFile = project.file("$project.rootDir/schema/json/${svc.filename}")
                    def json = new JsonSlurper().parse(specFile)

                    json["paths"].each { Map.Entry endpoint ->
                        endpoint.value.each { Map.Entry httpMethod ->
                            if (httpMethod.value.containsKey("tags") && httpMethod.value.tags instanceof List) {
                                // Rename tag associated with endpoint
                                httpMethod.value.tags = httpMethod.value.tags.collect { tag ->
                                    tag == "General" ? svc.name : tag
                                }
                            }
                        }
                    }
                    specFile.text = JsonOutput.prettyPrint(JsonOutput.toJson(json))
                }
            }
            project.tasks.named("generate$svc.name") { dependsOn ungroup }
        }

        // update OpenAPI file of the webhooks to add a custom extension 'x-webhook-root' to the model that represents the webhook payload
        // this is necessary to generate the WebhookHandler that deserialises the Webhook models
        project.ext.services.each { Service svc ->
            def addWebhookExtension = project.tasks.register("addWebhookExtension${svc.name}") {
                group 'specs'
                description "Add x-webhook-root extension to ${svc.name}"
                dependsOn ':specs'
                doLast {
                    def specFile = project.file("$project.rootDir/schema/json/${svc.filename}")
                    def json = new JsonSlurper().parse(specFile)

                    // Check if the service name ends with "Webhooks"
                    if (svc.name.endsWith("Webhooks") && json.containsKey("components") && json["components"].containsKey("schemas")) {
                        json["components"]["schemas"].each { Map.Entry schema ->
                            def properties = schema.value?.properties
                            // add 'x-webhook-root' to the webhook model (we find 'environment' and 'data' attributes)
                            if (properties?.containsKey("environment") && properties?.containsKey("data")) {
                                schema.value["x-webhook-root"] = true
                            }
                            // add 'x-webhook-root' to RelayedAuthenticationRequest model (missing 'environment' and 'data' attributes)
                            // bespoke fix as the model doesn't adopt the standard schema
                            if (schema.key == "RelayedAuthenticationRequest") {
                                schema.value["x-webhook-root"] = true
                            }
                            // add 'x-webhook-root' to DisputeNotificationRequest model
                            // bespoke fix as the model doesn't adopt the standard schema (missing 'environment' attribute)
                            if (schema.key == "DisputeNotificationRequest") {
                                schema.value["x-webhook-root"] = true
                            }
                        }
                    }

                    specFile.text = JsonOutput.prettyPrint(JsonOutput.toJson(json))
                }
            }
            project.tasks.named("generate$svc.name") { dependsOn addWebhookExtension }
        }

    }
}
