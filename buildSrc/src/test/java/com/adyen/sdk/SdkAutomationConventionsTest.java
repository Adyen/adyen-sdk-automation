package com.adyen.sdk;

import org.gradle.api.Project;
import org.gradle.testfixtures.ProjectBuilder;
import org.junit.Test;
import org.openapitools.generator.gradle.plugin.tasks.GenerateTask;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

public class SdkAutomationConventionsTest {
    @Test
    public void addsGenerateTaskToProject() {
        Project project = ProjectBuilder.builder().build();
        project.getPluginManager().apply("adyen.sdk-automation-conventions");

        assertTrue(project.getTasks().getByName("generateCheckout") instanceof GenerateTask);
        assertTrue(project.getExtensions().getExtraProperties().has("services"));
    }

    @Test
    public void addsWriteOpenApiCommitTaskToProject() {
        Project project = ProjectBuilder.builder().build();
        project.getPluginManager().apply("adyen.sdk-automation-conventions");

        // verify writeOpenApiCommit tasks are registered for each service
        assertTrue(project.getTasks().getNames().contains("writeOpenApiCommitCheckout"));
        assertTrue(project.getTasks().getNames().contains("writeOpenApiCommitBalancePlatform"));
        assertTrue(project.getTasks().getNames().contains("writeOpenApiCommitAcsWebhooks"));

        // verify the base service task depends on the writeOpenApiCommit task
        var checkoutTask = project.getTasks().getByName("checkout");
        var depNames = new java.util.HashSet<String>();
        checkoutTask.getDependsOn().forEach(dep -> {
            if (dep instanceof org.gradle.api.tasks.TaskProvider) {
                depNames.add(((org.gradle.api.tasks.TaskProvider<?>) dep).getName());
            }
        });
        assertTrue("checkout task should depend on writeOpenApiCommitCheckout", depNames.contains("writeOpenApiCommitCheckout"));
    }

    @Test
    public void serviceName() {
        var svc = new Service();
        svc.setName("Checkout");
        svc.setVersion(71);

        assertEquals("CheckoutService-v71.json", svc.getFilename());
    }
}
