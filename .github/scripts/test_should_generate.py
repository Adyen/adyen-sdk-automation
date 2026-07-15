#!/usr/bin/env python3

import subprocess
import sys
import tempfile
import unittest
import should_generate
from pathlib import Path


class TestShouldGenerate(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp_dir.name)
        self.run_git("init")
        self.run_git("config", "user.email", "test@example.com")
        self.run_git("config", "user.name", "Test User")
        self.commit_changes({"README.md": "initial\n"})

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def run_git(self, *args: str) -> str:
        return subprocess.run(
            ["git", *args],
            cwd=self.repo,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    def commit_changes(self, changes: dict[str, str]) -> str:
        for relative_path, content in changes.items():
            path = self.repo / relative_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        self.run_git("add", ".")
        self.run_git("commit", "-m", "test change")
        return self.run_git("rev-parse", "HEAD")

    def classify(self, changes: dict[str, str]) -> dict[str, str]:
        before = self.run_git("rev-parse", "HEAD")
        after = self.commit_changes(changes)
        decision = should_generate.classify_changes(before, after, self.repo)
        return {
            "should_generate": str(decision.should_generate).lower(),
            "reason": decision.reason,
        }

    def test_cli_writes_github_outputs(self) -> None:
        before = self.run_git("rev-parse", "HEAD")
        after = self.commit_changes({"README.md": "documentation\n"})
        output_path = self.repo / "output.txt"
        subprocess.run(
            [sys.executable, should_generate.__file__, before, after, str(output_path)],
            cwd=self.repo,
            check=True,
        )
        result = dict(line.split("=", 1) for line in output_path.read_text().splitlines())

        self.assertEqual(result["should_generate"], "false")
        self.assertEqual(result["reason"], "non-generation-changes-only")

    def test_skips_test_dependency_only_update(self) -> None:
        result = self.classify(
            {
                "buildSrc/build.gradle.kts": (
                    'testImplementation("org.junit.jupiter:junit-jupiter:6.1.2")\n'
                    'testRuntimeOnly("org.junit.platform:junit-platform-launcher")\n'
                )
            }
        )

        self.assertEqual(result["should_generate"], "false")
        self.assertEqual(result["reason"], "non-generation-changes-only")

    def test_generates_for_openapi_generator_dependency_update(self) -> None:
        result = self.classify(
            {
                "buildSrc/build.gradle.kts": (
                    'implementation("org.openapitools:openapi-generator-gradle-plugin:7.16.0")\n'
                )
            }
        )

        self.assertEqual(result["should_generate"], "true")
        self.assertEqual(result["reason"], "generation-affecting-change:buildSrc/build.gradle.kts")

    def test_generates_for_generator_source_change(self) -> None:
        result = self.classify({"buildSrc/src/main/kotlin/Service.kt": "class Service\n"})

        self.assertEqual(result["should_generate"], "true")
        self.assertEqual(result["reason"], "generation-affecting-change:buildSrc/src/main/kotlin/Service.kt")

    def test_generates_for_language_configuration_change(self) -> None:
        result = self.classify({"java/config.yaml": "library: jersey3\n"})

        self.assertEqual(result["should_generate"], "true")
        self.assertEqual(result["reason"], "generation-affecting-change:java/config.yaml")

    def test_generates_for_gradle_wrapper_change(self) -> None:
        result = self.classify({"gradle/wrapper/gradle-wrapper.properties": "distributionUrl=gradle-9.6-bin.zip\n"})

        self.assertEqual(result["should_generate"], "true")
        self.assertEqual(
            result["reason"],
            "generation-affecting-change:gradle/wrapper/gradle-wrapper.properties",
        )

    def test_skips_documentation_and_tests(self) -> None:
        result = self.classify(
            {
                "README.md": "documentation\n",
                "buildSrc/src/test/kotlin/ServiceTest.kt": "class ServiceTest\n",
            }
        )

        self.assertEqual(result["should_generate"], "false")
        self.assertEqual(result["reason"], "non-generation-changes-only")

    def test_skips_mixed_test_dependency_and_documentation_update(self) -> None:
        result = self.classify(
            {
                "README.md": "documentation\n",
                "buildSrc/build.gradle.kts": 'testImplementation("org.assertj:assertj-core:3.27.7")\n',
            }
        )

        self.assertEqual(result["should_generate"], "false")
        self.assertEqual(result["reason"], "non-generation-changes-only")

    def test_generates_for_ambiguous_build_file_change(self) -> None:
        result = self.classify({"buildSrc/build.gradle.kts": "repositories { mavenCentral() }\n"})

        self.assertEqual(result["should_generate"], "true")
        self.assertEqual(result["reason"], "generation-affecting-change:buildSrc/build.gradle.kts")

    def test_generates_for_unknown_change(self) -> None:
        result = self.classify({"renovate.json": "{}\n"})

        self.assertEqual(result["should_generate"], "true")
        self.assertEqual(result["reason"], "generation-affecting-change:renovate.json")


if __name__ == "__main__":
    unittest.main(verbosity=2)
