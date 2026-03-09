plugins {
    `kotlin-dsl`
}

repositories {
    mavenCentral()
    gradlePluginPortal()
}

// openapiGeneratorVersion is defined in buildSrc/gradle.properties
val openapiGeneratorVersion: String by project

dependencies {
    implementation("org.openapitools:openapi-generator-gradle-plugin:$openapiGeneratorVersion")
    implementation(localGroovy())
    testImplementation("org.junit.jupiter:junit-jupiter:5.14.3")
    testImplementation("org.assertj:assertj-core:3.24.2")
    testRuntimeOnly("org.junit.platform:junit-platform-launcher")
}

tasks.withType<Test> {
    useJUnitPlatform()
}
