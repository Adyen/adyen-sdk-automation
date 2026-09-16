package com.adyen.sdk;

import org.gradle.api.Project;
import org.gradle.testfixtures.ProjectBuilder;
import org.junit.jupiter.api.Test;

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
                        { "name": "Tapi", "spec": "TerminalAPI", "version": 1, "projects": ["java", "node"] },
                        { "name": "Management", "version": 3, "excludedProjects": ["go"] }
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
}
