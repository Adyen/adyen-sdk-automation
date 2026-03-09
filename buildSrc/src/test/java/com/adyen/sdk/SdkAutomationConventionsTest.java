package com.adyen.sdk;

import org.gradle.api.Project;
import org.gradle.testfixtures.ProjectBuilder;
import org.junit.Test;
import org.openapitools.generator.gradle.plugin.tasks.GenerateTask;
import com.adyen.sdk.SdkAutomationExtension;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

public class SdkAutomationConventionsTest {
    @Test
    public void addsGenerateTaskToProject() {
        Project project = ProjectBuilder.builder().build();
        project.getPluginManager().apply("adyen.sdk-automation-conventions");

        var task = project.getTasks().getByName("generateCheckout");
        assertTrue(task.getClass().getName().startsWith("org.openapitools.generator.gradle.plugin.tasks.GenerateTask"));
        assertTrue(project.getExtensions().findByName("sdkAutomation") instanceof SdkAutomationExtension);
    }

    @Test
    public void serviceName() {
        var svc = new Service("Checkout", null, 71, false);

        assertEquals("CheckoutService-v71.json", svc.getFilename());
    }
}
