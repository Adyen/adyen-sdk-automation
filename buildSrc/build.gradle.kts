plugins {
    `kotlin-dsl`
}

repositories {
    mavenCentral()
    gradlePluginPortal()
}

// openapiGeneratorVersion is defined in buildSrc/gradle.properties
// but can be overridden via system property: -DopenapiGeneratorVersion=7.11.0
val openapiGeneratorVersion: String = System.getProperty("openapiGeneratorVersion")
    ?: project.findProperty("openapiGeneratorVersion") as String

dependencies {
    implementation("org.openapitools:openapi-generator-gradle-plugin:$openapiGeneratorVersion")
    implementation(localGroovy())
    testImplementation("org.junit.jupiter:junit-jupiter:6.1.2")
    testImplementation("org.assertj:assertj-core:3.24.2")
    testRuntimeOnly("org.junit.platform:junit-platform-launcher")
}

tasks.withType<Test> {
    useJUnitPlatform()
}
