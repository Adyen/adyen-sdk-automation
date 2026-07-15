#!/usr/bin/env python3.13

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parent / "resolve-matrix-inputs.sh"

ALL_PROJECTS = ["java", "php", "node", "python", "ruby", "go", "dotnet"]
ALL_SERVICES = [
    "checkout",
    "capital",
    "payout",
    "recurring",
    "binlookup",
    "posmobile",
    "paymentsapp",
    "disputes",
    "storedvalue",
    "payment",
    "tapi",
    "management",
    "balancecontrol",
    "legalentitymanagement",
    "balanceplatform",
    "transfers",
    "dataprotection",
    "sessionauthentication",
    "configurationwebhooks",
    "acswebhooks",
    "reportwebhooks",
    "transferwebhooks",
    "transactionwebhooks",
    "managementwebhooks",
    "disputewebhooks",
    "negativebalancewarningwebhooks",
    "balancewebhooks",
    "tokenizationwebhooks",
    "relayedauthorizationwebhooks",
]


def run_script(projects: str = "", services: str = "") -> tuple[subprocess.CompletedProcess[str], dict[str, list[str]]]:
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".output", delete=False) as output_file:
        output_path = Path(output_file.name)

    try:
        env = {**os.environ, "INPUT_PROJECTS": projects, "INPUT_SERVICES": services}
        result = subprocess.run(
            ["bash", str(SCRIPT), str(output_path)],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

        outputs: dict[str, list[str]] = {}
        content = output_path.read_text().splitlines()
        for line in content:
            key, _, value = line.partition("=")
            if key:
                outputs[key] = json.loads(value)

        return result, outputs
    finally:
        output_path.unlink(missing_ok=True)


class TestResolveMatrixInputs(unittest.TestCase):
    def test_empty_inputs_return_full_defaults(self) -> None:
        result, outputs = run_script()
        self.assertEqual(result.returncode, 0)
        self.assertEqual(outputs["projects"], ALL_PROJECTS)
        self.assertEqual(outputs["services"], ALL_SERVICES)

    def test_single_valid_project(self) -> None:
        result, outputs = run_script(projects="java")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(outputs["projects"], ["java"])
        self.assertEqual(outputs["services"], ALL_SERVICES)

    def test_multiple_projects_with_spaces_and_trailing_comma(self) -> None:
        result, outputs = run_script(projects=" java , python , ")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(outputs["projects"], ["java", "python"])

    def test_invalid_project_exits_nonzero_with_error_message(self) -> None:
        result, outputs = run_script(projects="java,typo")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Invalid project(s): typo", result.stdout)
        self.assertEqual(outputs, {})

    def test_invalid_service_exits_nonzero_with_error_message(self) -> None:
        result, outputs = run_script(services="checkout,bad")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Invalid service(s): bad", result.stdout)
        self.assertEqual(outputs["projects"], ALL_PROJECTS)

    def test_all_invalid_projects_listed_in_error(self) -> None:
        result, _ = run_script(projects="typo1,typo2")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Invalid project(s): typo1, typo2", result.stdout)

    def test_mixed_valid_and_invalid_fails_without_partial_output(self) -> None:
        result, outputs = run_script(projects="java,typo")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(outputs, {})

    def test_valid_services_subset(self) -> None:
        result, outputs = run_script(services="checkout,management")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(outputs["services"], ["checkout", "management"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
