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
    public void serviceName() {
        var svc = new Service();
        svc.setName("Checkout");
        svc.setVersion(71);

        assertEquals("CheckoutService-v71.json", svc.getFilename());
    }
}
