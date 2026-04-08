package com.adyen.sdk;

import org.gradle.api.Project;
import org.gradle.testfixtures.ProjectBuilder;
import org.junit.jupiter.api.Test;
import org.openapitools.generator.gradle.plugin.tasks.GenerateTask;
import com.adyen.sdk.SdkAutomationExtension;

import static org.assertj.core.api.Assertions.assertThat;

public class SdkAutomationConventionsTest {
    @Test
    public void addsGenerateTaskToProject() {
        Project project = ProjectBuilder.builder().build();
        project.getPluginManager().apply("adyen.sdk-automation-conventions");

        var task = project.getTasks().getByName("generateCheckout");
        assertThat(task.getClass().getName()).startsWith("org.openapitools.generator.gradle.plugin.tasks.GenerateTask");
        assertThat(project.getExtensions().findByName("sdkAutomation")).isInstanceOf(SdkAutomationExtension.class);
    }

    @Test
    public void tapiTaskExistsForJava() {
        Project project = ProjectBuilder.builder().withName("java").build();
        project.getPluginManager().apply("adyen.sdk-automation-conventions");

        assertThat(project.getTasks().findByName("tapi")).isNotNull();
        assertThat(project.getTasks().findByName("generateTapi")).isNotNull();
    }

    @Test
    public void tapiTaskDoesNotExistForGo() {
        Project project = ProjectBuilder.builder().withName("go").build();
        project.getPluginManager().apply("adyen.sdk-automation-conventions");

        assertThat(project.getTasks().findByName("tapi")).isNull();
        assertThat(project.getTasks().findByName("generateTapi")).isNull();
    }

    @Test
    public void serviceName() {
        var svc = new Service("Checkout", null, 71, false, null);

        assertThat(svc.getFilename()).isEqualTo("CheckoutService-v71.json");
    }
}
