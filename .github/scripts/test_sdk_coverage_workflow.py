#!/usr/bin/env python3

import json
import os
import re
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


WORKFLOW = Path(__file__).parents[1] / "workflows" / "sdk-coverage.yaml"


class TestSdkCoverageWorkflow(unittest.TestCase):
    def setUp(self) -> None:
        self.workflow = WORKFLOW.read_text()
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bin_dir = self.root / "bin"
        self.bin_dir.mkdir()
        self.report_dir = self.root / "reports"
        self.summary = self.root / "summary.md"
        self.arguments = self.root / "arguments.json"
        stub = self.bin_dir / "python3"
        stub.write_text(
            f"#!{sys.executable}\n"
            "import json, os, sys\n"
            "from pathlib import Path\n"
            "Path(os.environ['ARGUMENTS_FILE']).write_text(json.dumps(sys.argv[1:]))\n"
            "if os.environ.get('WRITE_REPORT', '1') == '1':\n"
            "    (Path(os.environ['REPORT_DIR']) / 'sdk-coverage.md').write_text("
            "'# SDK coverage\\n\\n| Service | Java | Node | Python | PHP | Ruby | Go | .NET |\\n')\n"
            "for _ in range(int(os.environ.get('LOG_LINE_COUNT', '1'))):\n"
            "    print('Generation log output')\n"
            "print('Generation stderr output', file=sys.stderr)\n"
            "sys.exit(int(os.environ.get('GENERATOR_EXIT_CODE', '0')))\n"
        )
        stub.chmod(0o755)

    def step(self, name: str) -> str:
        match = re.search(
            rf"(?ms)^      - name: {re.escape(name)}\n(.*?)(?=^      - |\Z)",
            self.workflow,
        )
        self.assertIsNotNone(match, f"Missing workflow step: {name}")
        return match.group(1)

    def run_step(self, name: str, **overrides: str) -> subprocess.CompletedProcess:
        script = textwrap.dedent(self.step(name).split("        run: |\n", 1)[1])
        return subprocess.run(
            ["bash", "-eo", "pipefail", "-c", script],
            cwd=self.root,
            env={
                **os.environ,
                "PATH": str(self.bin_dir) + os.pathsep + os.environ.get("PATH", ""),
                "REPORT_DIR": str(self.report_dir),
                "GITHUB_STEP_SUMMARY": str(self.summary),
                "ARGUMENTS_FILE": str(self.arguments),
                "SERVICES": "",
                **overrides,
            },
            capture_output=True,
            text=True,
            check=False,
        )

    def test_coverage_workflows_have_distinct_run_names(self) -> None:
        for filename, name in (
            ("sdk-coverage.yaml", "SDK Coverage"),
            ("spec-coverage.yaml", "Spec Coverage"),
        ):
            with self.subTest(workflow=filename):
                content = (WORKFLOW.parent / filename).read_text()
                self.assertRegex(content, rf"(?m)^run-name: {re.escape(name)}$")

    def test_manual_and_scoped_pull_request_triggers(self) -> None:
        self.assertIn("  workflow_dispatch:\n", self.workflow)
        self.assertIn("  pull_request:\n", self.workflow)
        self.assertIn('    branches: [ "main" ]\n', self.workflow)
        for path in (
            "config/services.json",
            "config/spec-coverage-baseline.json",
            ".github/scripts/sdk_coverage.py",
            ".github/scripts/check_spec_coverage.py",
            ".github/workflows/sdk-coverage.yaml",
            "buildSrc/**",
        ):
            with self.subTest(path=path):
                self.assertIn(f"      - '{path}'\n", self.workflow)
        self.assertNotRegex(self.workflow, r"(?m)^  (push|pull_request_target):")

    def test_weekday_morning_schedule(self) -> None:
        self.assertIn("  schedule:\n    - cron: '30 7 * * 1-5'\n", self.workflow)

    def test_workflow_is_read_only_and_actions_are_pinned(self) -> None:
        self.assertIn("permissions:\n  contents: read\n", self.workflow)
        self.assertIn("          persist-credentials: false\n", self.workflow)
        self.assertNotIn("secrets.", self.workflow)
        self.assertNotIn("continue-on-error:", self.workflow)
        for action in re.findall(r"(?m)^\s+(?:- )?uses: (.+)$", self.workflow):
            with self.subTest(action=action):
                self.assertRegex(action, r"^[\w/-]+@[0-9a-f]{40}(?:\s+#.*)?$")

    def test_pr_lookup_uses_read_only_workflow_token(self) -> None:
        self.assertIn("  pull-requests: read\n", self.workflow)
        self.assertIn("          GH_TOKEN: ${{ github.token }}\n", self.step("Generate detailed SDK report"))

    def test_default_run_checks_all_services_and_captures_log(self) -> None:
        result = self.run_step("Generate detailed SDK report")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            json.loads(self.arguments.read_text()),
            [
                "-u", ".github/scripts/sdk_coverage.py", "--jobs", "2",
                "--output", str(self.report_dir / "sdk-coverage.md"),
            ],
        )
        self.assertIn("Generation log output", (self.report_dir / "sdk-coverage.log").read_text())

    def test_verbose_diagnostics_only_go_to_artifact_log(self) -> None:
        result = self.run_step("Generate detailed SDK report", LOG_LINE_COUNT="1000")
        self.assertEqual(result.returncode, 0, result.stderr)
        log = (self.report_dir / "sdk-coverage.log").read_text()
        self.assertEqual(log.count("Generation log output"), 1000)
        self.assertIn("Generation stderr output", log)
        self.assertNotIn("Generation log output", result.stdout + result.stderr)
        self.assertNotIn("Generation stderr output", result.stdout + result.stderr)
        self.assertIn("sdk-coverage artifact", result.stdout)
        self.assertLess(len(result.stdout + result.stderr), 500)

    def test_service_input_is_passed_as_one_literal_argument(self) -> None:
        services = "checkout,management; touch injected"
        result = self.run_step("Generate detailed SDK report", SERVICES=services)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(self.arguments.read_text())[-1], f"--services={services}")
        self.assertFalse((self.root / "injected").exists())

    def test_generator_failure_is_preserved_and_report_is_published(self) -> None:
        generated = self.run_step("Generate detailed SDK report", GENERATOR_EXIT_CODE="1")
        self.assertEqual(generated.returncode, 1)
        self.assertTrue((self.report_dir / "sdk-coverage.log").is_file())
        self.assertIn("exit code 1", generated.stdout)
        self.assertNotIn("Generation log output", generated.stdout + generated.stderr)
        self.assertIn("Generation stderr output", (self.report_dir / "sdk-coverage.log").read_text())
        published = self.run_step("Publish report summary")
        self.assertEqual(published.returncode, 0, published.stderr)
        self.assertEqual(self.summary.read_text(), (self.report_dir / "sdk-coverage.md").read_text())
        logged = self.run_step("Print report to log")
        self.assertEqual(logged.returncode, 0, logged.stderr)
        self.assertEqual(logged.stdout, (self.report_dir / "sdk-coverage.md").read_text())

    def test_failure_before_report_creation_still_captures_log(self) -> None:
        result = self.run_step(
            "Generate detailed SDK report", GENERATOR_EXIT_CODE="2", WRITE_REPORT="0",
        )
        self.assertEqual(result.returncode, 2)
        self.assertTrue((self.report_dir / "sdk-coverage.log").is_file())
        self.assertFalse((self.report_dir / "sdk-coverage.md").exists())

    def test_summary_explains_missing_report_after_setup_failure(self) -> None:
        result = self.run_step("Publish report summary")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("No detailed SDK report was produced.", self.summary.read_text())

    def test_prints_full_report_including_audit_and_notes(self) -> None:
        report = (
            "# SDK coverage\n\n"
            "## OpenAPI catalog audit\n\n"
            "| OpenAPI family | Latest version | Already in SDK | Baseline reason |\n"
            "| ExampleService | 2 | In SDK at v1 | Reviewed gap |\n\n"
            "## SDK generation coverage\n\n"
            "| Service | Java |\n| Example | Current v1 |\n\n"
            "Notes:\n\n- Coverage differences are warnings.\n"
        )
        self.report_dir.mkdir()
        report_path = self.report_dir / "sdk-coverage.md"
        report_path.write_text(report)
        result = self.run_step("Print report to log")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, report)
        self.assertEqual(report_path.read_text(), report)

    def test_print_step_handles_missing_report(self) -> None:
        result = self.run_step("Print report to log")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("No detailed SDK report was produced.", result.stdout)

    def test_summary_logs_and_artifacts_run_after_failures(self) -> None:
        self.assertIn("        if: always()\n", self.step("Publish report summary"))
        self.assertIn("        if: always()\n", self.step("Print report to log"))
        self.assertLess(
            self.workflow.index("- name: Publish report summary"),
            self.workflow.index("- name: Print report to log"),
        )
        self.assertLess(
            self.workflow.index("- name: Print report to log"),
            self.workflow.index("- name: Upload report and log"),
        )
        upload = self.step("Upload report and log")
        self.assertIn("        if: always()\n", upload)
        self.assertIn("          name: sdk-coverage\n", upload)
        self.assertIn("          path: ${{ env.REPORT_DIR }}/\n", upload)

    def test_go_formatter_binary_directory_is_added_to_path(self) -> None:
        script = self.step("Add Go formatter tools to PATH")
        self.assertIn('echo "$(go env GOPATH)/bin" >> "$GITHUB_PATH"', script)


if __name__ == "__main__":
    unittest.main()
