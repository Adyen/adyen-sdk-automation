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
    testImplementation("junit:junit:4.13.2")
}
