#!/usr/bin/env python3

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parent / "resolve-matrix-inputs.sh"
CATALOG = Path(__file__).parents[2] / "config" / "services.json"

ALL_PROJECTS = ["java", "php", "node", "python", "ruby", "go", "dotnet"]

# Expected services and excludes come from the catalog (the single source of truth).
with CATALOG.open() as catalog_file:
    _catalog = json.load(catalog_file)

ALL_SERVICES = [service["name"].lower() for service in _catalog["services"]]

# A tiny synthetic catalog with hardcoded expectation.
PINNED_CATALOG = {
    "services": [
        {"name": "Alpha", "version": 1},
        {"name": "Beta", "version": 2, "projects": ["java", "node"]},
        {"name": "Gamma", "version": 3, "excludedProjects": ["go"]},
    ]
}
PINNED_SERVICES = ["alpha", "beta", "gamma"]
PINNED_EXCLUDES = [
    {"project": "php", "service": "beta"},
    {"project": "python", "service": "beta"},
    {"project": "ruby", "service": "beta"},
    {"project": "go", "service": "beta"},
    {"project": "dotnet", "service": "beta"},
    {"project": "go", "service": "gamma"},
]


def run_script(projects: str = "", services: str = "", catalog: dict | None = None) -> tuple[subprocess.CompletedProcess[str], dict[str, list]]:
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".output", delete=False) as output_file:
        output_path = Path(output_file.name)

    catalog_path = None
    if catalog is not None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as catalog_file:
            json.dump(catalog, catalog_file)
            catalog_path = Path(catalog_file.name)

    try:
        env = {**os.environ, "INPUT_PROJECTS": projects, "INPUT_SERVICES": services}
        if catalog_path is not None:
            env["SERVICES_CATALOG"] = str(catalog_path)
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
        if catalog_path is not None:
            catalog_path.unlink(missing_ok=True)


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

    def test_pinned_catalog_services_and_excludes(self) -> None:
        result, outputs = run_script(catalog=PINNED_CATALOG)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(outputs["services"], PINNED_SERVICES)
        self.assertEqual(outputs["excludes"], PINNED_EXCLUDES)

    def test_excludes_output_present_with_custom_inputs(self) -> None:
        result, outputs = run_script(projects="java", services="alpha", catalog=PINNED_CATALOG)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(outputs["services"], ["alpha"])
        self.assertEqual(outputs["excludes"], PINNED_EXCLUDES)


if __name__ == "__main__":
    unittest.main(verbosity=2)
