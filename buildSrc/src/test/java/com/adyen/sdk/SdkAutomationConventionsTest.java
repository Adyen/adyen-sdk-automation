package com.adyen.sdk;

import org.gradle.api.Project;
import org.gradle.api.Task;
import org.gradle.testfixtures.ProjectBuilder;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.openapitools.generator.gradle.plugin.tasks.GenerateTask;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.file.Files;
import java.nio.file.Path;

import static org.assertj.core.api.Assertions.assertThat;

public class SdkAutomationConventionsTest {
    /**
     * The conventions plugin loads the service catalog from config/services.json at
     * configuration time, so test projects need a (minimal) catalog in their project dir.
     */
    private static Project projectWithCatalog(String name) {
        Project project = ProjectBuilder.builder().withName(name).build();
        Path configDir = project.getProjectDir().toPath().resolve("config");
        try {
            Files.createDirectories(configDir);
            Files.writeString(configDir.resolve("services.json"), """
                    {
                      "services": [
                        { "name": "Checkout", "version": 72 },
                        { "name": "Recurring", "version": 68, "small": true },
                        { "name": "SoftPOSConfiguration", "version": 3 },
                        { "name": "Tapi", "spec": "TerminalAPI", "version": 1, "projects": ["java", "node"] },
                        { "name": "Management", "version": 3, "excludedProjects": ["go"] },
                        { "name": "AcsWebhooks", "version": 1 }
                      ]
                    }
                    """);
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
        return project;
    }

    @Test
    public void addsGenerateTaskToProject() {
        Project project = projectWithCatalog("java");
        project.getPluginManager().apply("adyen.sdk-automation-conventions");

        var task = project.getTasks().getByName("generateCheckout");
        assertThat(task.getClass().getName()).startsWith("org.openapitools.generator.gradle.plugin.tasks.GenerateTask");
        assertThat(project.getExtensions().findByName("sdkAutomation")).isInstanceOf(SdkAutomationExtension.class);
    }

    @Test
    public void tapiTaskExistsForJava() {
        Project project = projectWithCatalog("java");
        project.getPluginManager().apply("adyen.sdk-automation-conventions");

        assertThat(project.getTasks().findByName("tapi")).isNotNull();
        assertThat(project.getTasks().findByName("generateTapi")).isNotNull();
    }

    @ParameterizedTest
    @ValueSource(strings = {"java", "php", "node", "python", "ruby", "go", "dotnet"})
    public void softposConfigurationUsesV3SpecForEveryProject(String name) {
        Project project = projectWithCatalog(name);
        project.getPluginManager().apply("adyen.sdk-automation-conventions");

        var task = (GenerateTask) project.getTasks().getByName("generateSoftPOSConfiguration");
        assertThat(task.getInputSpec().get()).isEqualTo(
                project.getLayout().getBuildDirectory().file("specs/SoftPOSConfigurationService-v3.json")
                        .get().getAsFile().getAbsolutePath());
        assertThat(task.getTaskDependencies().getDependencies(task))
                .extracting(Task::getName)
                .contains("prepareSpecSoftPOSConfiguration");
        var serviceTask = project.getTasks().getByName("softposconfiguration");
        assertThat(serviceTask.getTaskDependencies().getDependencies(serviceTask))
                .extracting(Task::getName)
                .contains(task.getName());
        var allServicesTask = project.getTasks().getByName("services");
        assertThat(allServicesTask.getTaskDependencies().getDependencies(allServicesTask))
                .extracting(Task::getName)
                .contains(serviceTask.getName());
    }

    @Test
    public void tapiTaskDoesNotExistForGo() {
        Project project = projectWithCatalog("go");
        project.getPluginManager().apply("adyen.sdk-automation-conventions");

        assertThat(project.getTasks().findByName("tapi")).isNull();
        assertThat(project.getTasks().findByName("generateTapi")).isNull();
    }

    @Test
    public void managementTaskExistsForJava() {
        Project project = projectWithCatalog("java");
        project.getPluginManager().apply("adyen.sdk-automation-conventions");

        assertThat(project.getTasks().findByName("management")).isNotNull();
        assertThat(project.getTasks().findByName("generateManagement")).isNotNull();
    }

    @Test
    public void managementTaskDoesNotExistForGo() {
        Project project = projectWithCatalog("go");
        project.getPluginManager().apply("adyen.sdk-automation-conventions");

        assertThat(project.getTasks().findByName("management")).isNull();
        assertThat(project.getTasks().findByName("generateManagement")).isNull();
    }

    private static final String SOURCE_SPEC = """
            {
              "openapi": "3.1.0",
              "paths": { "/t": { "post": { "tags": ["General"], "operationId": "post-t", "x-methodName": "postT" } } },
              "components": { "schemas": {
                "Amount": { "properties": { "currency": { "type": ["string", "null"] } } },
                "AcsWebhook": { "properties": { "environment": {}, "data": {} } }
              } }
            }
            """;

    /** Writes the source spec into the clone location and runs the staging task in place. */
    private static String stage(Project project, String service, String filename) throws IOException {
        Path source = project.getRootDir().toPath().resolve("schema/json/" + filename);
        Files.createDirectories(source.getParent());
        Files.writeString(source, SOURCE_SPEC);

        Task task = project.getTasks().getByName("prepareSpec" + service);
        task.getActions().forEach(action -> action.execute(task));

        assertThat(Files.readString(source)).as("source spec stays pristine").isEqualTo(SOURCE_SPEC);
        var generate = (GenerateTask) project.getTasks().getByName("generate" + service);
        return Files.readString(Path.of(generate.getInputSpec().get()));
    }

    @ParameterizedTest
    @ValueSource(strings = {"java", "php", "node", "python", "ruby", "dotnet"})
    public void nonGoProjectsStageA300Spec(String name) throws IOException {
        Project project = projectWithCatalog(name);
        project.getPluginManager().apply("adyen.sdk-automation-conventions");

        String staged = stage(project, "Recurring", "RecurringService-v68.json");

        assertThat(staged).contains("\"openapi\": \"3.0.0\"").contains("\"operationId\": \"postT\"");
    }

    @Test
    public void goStagesTheSourceOpenApiVersion() throws IOException {
        Project project = projectWithCatalog("go");
        project.getPluginManager().apply("adyen.sdk-automation-conventions");
        var extension = project.getExtensions().getByType(SdkAutomationExtension.class);
        extension.getRemoveTags().set(false);
        extension.getPreserveOpenApiVersion().set(true);

        String staged = stage(project, "Recurring", "RecurringService-v68.json");

        assertThat(staged).contains("\"openapi\": \"3.1.0\"")
                .contains("\"operationId\": \"postT\"")
                .contains("\"General\"")
                .containsSubsequence("\"type\": [", "\"string\"", "\"null\"");
    }

    @Test
    public void smallServicesRenameTheGeneralTagUnlessRemoveTagsIsOff() throws IOException {
        Project java = projectWithCatalog("java");
        java.getPluginManager().apply("adyen.sdk-automation-conventions");
        assertThat(stage(java, "Recurring", "RecurringService-v68.json"))
                .contains("\"Recurring\"").doesNotContain("\"General\"");

        Project php = projectWithCatalog("php");
        php.getPluginManager().apply("adyen.sdk-automation-conventions");
        php.getExtensions().getByType(SdkAutomationExtension.class).getRemoveTags().set(false);
        assertThat(stage(php, "Recurring", "RecurringService-v68.json")).contains("\"General\"");

        // Only small services are renamed.
        assertThat(stage(java, "Checkout", "CheckoutService-v72.json")).contains("\"General\"");
    }

    @ParameterizedTest
    @ValueSource(strings = {"java", "go"})
    public void onlyWebhookSpecsAreMarkedWithWebhookRoots(String name) throws IOException {
        Project project = projectWithCatalog(name);
        project.getPluginManager().apply("adyen.sdk-automation-conventions");

        assertThat(stage(project, "AcsWebhooks", "AcsWebhooksService-v1.json"))
                .contains("\"x-webhook-root\": true")
                .contains("\"x-has-at-least-one-webhook-root\": true");
        assertThat(stage(project, "Checkout", "CheckoutService-v72.json")).doesNotContain("x-webhook-root");
    }}
