#!/usr/bin/env python3

"""Validation tests for config/services.json, the single source of truth for the SDK service matrix.

These tests guard the relocated risk of centralizing the matrix in one file:
a malformed catalog would break every Gradle invocation at configuration time
and corrupt the CI matrix, so PRs are gated on these checks.
"""

import json
import unittest
from pathlib import Path

CATALOG = Path(__file__).parents[2] / "config" / "services.json"

# Mirrors the Gradle subprojects in settings.gradle.kts
KNOWN_PROJECTS = {"java", "php", "node", "python", "ruby", "go", "dotnet"}

SUPPORTED_CATALOG_FIELDS = {"services"}
SUPPORTED_SERVICE_FIELDS = {
    "name",
    "version",
    "spec",
    "small",
    "group",
    "projects",
    "excludedProjects",
}


def load_catalog() -> dict:
    with CATALOG.open() as catalog_file:
        return json.load(catalog_file)


class TestServicesCatalog(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = load_catalog()
        cls.services = cls.catalog.get("services", [])

    def test_catalog_fields_are_supported(self) -> None:
        unknown = set(self.catalog) - SUPPORTED_CATALOG_FIELDS
        self.assertEqual(unknown, set(), f"Unknown catalog field(s): {unknown}")
        self.assertIn("services", self.catalog, "catalog must contain a services field")

        for service in self.services:
            with self.subTest(service=service.get("name")):
                unknown = set(service) - SUPPORTED_SERVICE_FIELDS
                self.assertEqual(unknown, set(), f"Unknown service field(s): {unknown}")

    def test_catalog_is_not_empty(self) -> None:
        self.assertGreater(len(self.services), 0)

    def test_service_ids_are_unique(self) -> None:
        ids = [service["name"].lower() for service in self.services]
        duplicates = {service_id for service_id in ids if ids.count(service_id) > 1}
        self.assertEqual(duplicates, set(), f"Duplicate service ids: {duplicates}")

    def test_required_fields_are_well_typed(self) -> None:
        for service in self.services:
            with self.subTest(service=service.get("name")):
                self.assertIsInstance(service.get("name"), str)
                self.assertTrue(service["name"], "name must not be empty")
                # Service ids are lowercased independently by Kotlin, jq and Python;
                # restricting names to ASCII keeps the three implementations in agreement.
                self.assertRegex(service["name"], r"^[A-Za-z][A-Za-z0-9]*$", "name must be ASCII alphanumeric")
                # bool is a subclass of int, so check for it explicitly
                self.assertIsInstance(service.get("version"), int)
                self.assertNotIsInstance(service["version"], bool, "version must be an int")
                self.assertGreater(service["version"], 0, "version must be a positive int")

    def test_optional_fields_are_well_typed(self) -> None:
        # `group` is documentation-only and intentionally not checked: nothing consumes it.
        for service in self.services:
            with self.subTest(service=service.get("name")):
                if "spec" in service:
                    self.assertIsInstance(service["spec"], str, "spec must be a string")
                if "small" in service:
                    self.assertIsInstance(service["small"], bool, "small must be a boolean")
                # Entry types are covered by test_projects_and_excluded_projects_reference_known_projects
                for field in ("projects", "excludedProjects"):
                    if field in service:
                        self.assertIsInstance(service[field], list, f"{field} must be a list")

    def test_projects_and_excluded_projects_reference_known_projects(self) -> None:
        for service in self.services:
            with self.subTest(service=service.get("name")):
                for field in ("projects", "excludedProjects"):
                    unknown = set(service.get(field, [])) - KNOWN_PROJECTS
                    self.assertEqual(unknown, set(), f"Unknown project(s) in {field}: {unknown}")

    def test_projects_and_excluded_projects_are_mutually_exclusive(self) -> None:
        for service in self.services:
            with self.subTest(service=service.get("name")):
                self.assertFalse(
                    "projects" in service and "excludedProjects" in service,
                    "A service must use either projects (whitelist) or excludedProjects, not both",
                )

    def test_projects_whitelist_is_not_empty(self) -> None:
        # An empty projects whitelist would exclude the service from every project,
        # locally and in the CI matrix. That is almost certainly a mistake.
        for service in self.services:
            with self.subTest(service=service.get("name")):
                if "projects" in service:
                    self.assertTrue(
                        service["projects"],
                        "projects must not be empty; omit the field to include all projects",
                    )

if __name__ == "__main__":
    unittest.main(verbosity=2)
