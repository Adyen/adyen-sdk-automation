plugins {
    `kotlin-dsl`
    kotlin("plugin.serialization") version "2.3.0"
}

repositories {
    mavenCentral()
    gradlePluginPortal()
}

// openapiGeneratorVersion is defined in buildSrc/gradle.properties
val openapiGeneratorVersion: String by project

dependencies {
    implementation("org.openapitools:openapi-generator-gradle-plugin:$openapiGeneratorVersion")
    implementation("org.jetbrains.kotlinx:kotlinx-serialization-json:1.10.0")
    testImplementation("junit:junit:4.13.2")
}
