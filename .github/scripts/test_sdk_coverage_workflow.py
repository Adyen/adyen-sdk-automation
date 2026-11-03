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
            "print('Generation log output')\n"
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
        published = self.run_step("Publish report summary")
        self.assertEqual(published.returncode, 0, published.stderr)
        self.assertEqual(self.summary.read_text(), (self.report_dir / "sdk-coverage.md").read_text())

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

    def test_summary_and_artifacts_run_after_failures(self) -> None:
        self.assertIn("        if: always()\n", self.step("Publish report summary"))
        upload = self.step("Upload report and log")
        self.assertIn("        if: always()\n", upload)
        self.assertIn("          name: sdk-coverage\n", upload)
        self.assertIn("          path: ${{ env.REPORT_DIR }}/\n", upload)

    def test_go_formatter_binary_directory_is_added_to_path(self) -> None:
        script = self.step("Add Go formatter tools to PATH")
        self.assertIn('echo "$(go env GOPATH)/bin" >> "$GITHUB_PATH"', script)


if __name__ == "__main__":
    unittest.main()
