#!/usr/bin/env python3

"""Tests for the shared spec, catalog, and baseline evaluator."""

import json
import tempfile
import unittest
from pathlib import Path

import spec_coverage_core as coverage

REPO_BASELINE = coverage.DEFAULT_BASELINE
EMPTY_BASELINE = {"uncoveredSpecs": {}, "pinnedVersions": {}}


def baseline(uncovered: dict | None = None, pinned: dict | None = None) -> dict:
    return {"uncoveredSpecs": uncovered or {}, "pinnedVersions": pinned or {}}


class TestSpecDiscovery(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.specs_dir = Path(self.temp_dir.name)

    def write(self, *filenames: str) -> None:
        for filename in filenames:
            (self.specs_dir / filename).write_text("{}")

    def test_versions_are_grouped_per_spec(self) -> None:
        self.write("CheckoutService-v71.json", "CheckoutService-v72.json", "PaymentService-v68.json")
        self.assertEqual(
            coverage.discover_specs(self.specs_dir),
            {"CheckoutService": [71, 72], "PaymentService": [68]},
        )

    def test_unversioned_files_are_ignored(self) -> None:
        self.write("CheckoutService-v72.json", "openapi.json", "CheckoutService.json")
        self.assertEqual(coverage.discover_specs(self.specs_dir), {"CheckoutService": [72]})

    def test_missing_directory_is_reported(self) -> None:
        with self.assertRaises(FileNotFoundError):
            coverage.discover_specs(self.specs_dir / "absent")

    def test_empty_directory_is_reported(self) -> None:
        with self.assertRaises(FileNotFoundError):
            coverage.discover_specs(self.specs_dir)

    def test_public_discovery_skips_only_explicitly_non_public_versions(self) -> None:
        self.write("CheckoutService-v72.json", "CheckoutService-v73.json", "PrivateService-v1.json")
        for name in ("CheckoutService-v73.json", "PrivateService-v1.json"):
            (self.specs_dir / name).write_text(json.dumps({"info": {"x-publicVersion": False}}))
        self.assertEqual(
            coverage.discover_specs(self.specs_dir, public_only=True),
            {"CheckoutService": [72]},
        )
        self.assertEqual(coverage.discover_specs(self.specs_dir)["CheckoutService"], [72, 73])

    def test_all_non_public_specs_produce_an_empty_public_catalog(self) -> None:
        (self.specs_dir / "PrivateService-v1.json").write_text(
            json.dumps({"info": {"x-publicVersion": False}})
        )
        self.assertEqual(coverage.discover_specs(self.specs_dir, public_only=True), {})


class TestCatalogValidation(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.path = Path(self.temp_dir.name) / "services.json"

    def load(self, content) -> list[dict]:
        self.path.write_text(json.dumps(content))
        return coverage.load_catalog(self.path)

    def test_valid_catalog_is_returned(self) -> None:
        services = [{"name": "Checkout", "version": 72, "projects": ["java"]}]
        self.assertEqual(self.load({"services": services}), services)

    def test_invalid_catalog_documents_are_rejected(self) -> None:
        for document in ([], None, {}, {"services": []}, {"services": [], "other": True}):
            with self.subTest(document=document), self.assertRaises(ValueError):
                self.load(document)

    def test_invalid_service_values_are_rejected(self) -> None:
        entries = [
            {"name": ""},
            {"name": "../Checkout"},
            {"name": 42},
            {"version": 0},
            {"version": True},
            {"spec": None},
            {"small": "false"},
            {"projects": []},
            {"projects": "java"},
            {"projects": ["unknown"]},
            {"excludedProjects": [True]},
            {"projects": ["java"], "excludedProjects": ["go"]},
            {"unknown": True},
        ]
        for fields in entries:
            service = {"name": "Checkout", "version": 72, **fields}
            with self.subTest(service=service), self.assertRaises(ValueError):
                self.load({"services": [service]})

    def test_non_object_service_entries_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.load({"services": [None]})

    def test_duplicate_service_ids_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.load({"services": [
                {"name": "Checkout", "version": 72},
                {"name": "checkout", "version": 72},
            ]})


class TestSpecName(unittest.TestCase):
    def test_defaults_to_name_service(self) -> None:
        self.assertEqual(coverage.spec_name({"name": "Checkout", "version": 72}), "CheckoutService")

    def test_explicit_spec_wins(self) -> None:
        self.assertEqual(
            coverage.spec_name({"name": "Transfers", "spec": "TransferService", "version": 4}),
            "TransferService",
        )


class TestUncoveredSpecs(unittest.TestCase):
    def test_uncatalogued_spec_is_reported_without_claiming_sdk_absence(self) -> None:
        findings = coverage.evaluate({"FundService": [6]}, [], EMPTY_BASELINE)
        self.assertEqual(findings[0].kind, coverage.UNCOVERED)
        self.assertEqual(findings[0].detail, "published up to v6, absent from the generation catalog")

    def test_spec_without_catalog_entry_is_reported(self) -> None:
        findings = coverage.evaluate(
            {"CheckoutService": [72], "ForeignExchangeService": [1]},
            [{"name": "Checkout", "version": 72}],
            EMPTY_BASELINE,
        )
        self.assertEqual(
            [(finding.kind, finding.spec, finding.accepted) for finding in findings],
            [(coverage.UNCOVERED, "ForeignExchangeService", False)],
        )

    def test_baselined_spec_is_accepted_across_new_releases(self) -> None:
        findings = coverage.evaluate(
            {"AccountService": [3, 4, 5, 6, 7]},
            [],
            baseline(uncovered={"AccountService": {"reason": "Classic Platforms"}}),
        )
        self.assertEqual([finding.accepted for finding in findings], [True])

    def test_covered_spec_produces_no_finding(self) -> None:
        findings = coverage.evaluate(
            {"CheckoutService": [71, 72]},
            [{"name": "Checkout", "version": 72}],
            EMPTY_BASELINE,
        )
        self.assertEqual(findings, [])


class TestOutdatedVersions(unittest.TestCase):
    def test_catalog_behind_newest_spec_is_reported(self) -> None:
        findings = coverage.evaluate(
            {"BalanceControlService": [1, 2]},
            [{"name": "BalanceControl", "version": 1}],
            EMPTY_BASELINE,
        )
        self.assertEqual([(finding.kind, finding.accepted) for finding in findings],
                         [(coverage.BEHIND, False)])
        self.assertIn("v1", findings[0].detail)
        self.assertIn("v2", findings[0].detail)

    def test_pin_acknowledged_for_the_newest_version_is_accepted(self) -> None:
        findings = coverage.evaluate(
            {"BalanceControlService": [1, 2]},
            [{"name": "BalanceControl", "version": 1}],
            baseline(pinned={"BalanceControlService": {"acknowledgedVersion": 2, "reason": "breaking"}}),
        )
        self.assertEqual([finding.accepted for finding in findings], [True])

    def test_pin_acknowledged_for_an_older_version_fires_again(self) -> None:
        findings = coverage.evaluate(
            {"BalanceControlService": [1, 2, 3]},
            [{"name": "BalanceControl", "version": 1}],
            baseline(pinned={"BalanceControlService": {"acknowledgedVersion": 2, "reason": "breaking"}}),
        )
        self.assertEqual([(finding.kind, finding.accepted) for finding in findings],
                         [(coverage.BEHIND, False)])

    def test_missing_pin_is_reported_even_if_family_exists(self) -> None:
        findings = coverage.evaluate(
            {"CheckoutService": [72]},
            [{"name": "Checkout", "version": 73}],
            EMPTY_BASELINE,
        )
        missing = next(finding for finding in findings if finding.kind == coverage.MISSING)
        self.assertEqual(missing.service_name, "Checkout")
        self.assertFalse(missing.accepted)

    def test_existing_non_public_pin_is_not_reported_missing(self) -> None:
        findings = coverage.evaluate(
            {"CheckoutService": [72]},
            [{"name": "Checkout", "version": 73}],
            EMPTY_BASELINE,
            available_specs={"CheckoutService": [72, 73]},
        )
        self.assertEqual(findings, [])


class TestStaleBaseline(unittest.TestCase):
    def test_uncovered_entry_for_a_covered_spec_is_reported(self) -> None:
        findings = coverage.evaluate(
            {"CheckoutService": [72]},
            [{"name": "Checkout", "version": 72}],
            baseline(uncovered={"CheckoutService": {"reason": "stale"}}),
        )
        self.assertEqual([(finding.kind, finding.accepted) for finding in findings],
                         [(coverage.STALE, False)])

    def test_uncovered_entry_for_an_unpublished_spec_is_reported(self) -> None:
        findings = coverage.evaluate(
            {"CheckoutService": [72]},
            [{"name": "Checkout", "version": 72}],
            baseline(uncovered={"RemovedService": {"reason": "stale"}}),
        )
        self.assertEqual([finding.kind for finding in findings], [coverage.STALE])

    def test_pin_entry_that_is_no_longer_behind_is_reported(self) -> None:
        findings = coverage.evaluate(
            {"BalanceControlService": [1, 2]},
            [{"name": "BalanceControl", "version": 2}],
            baseline(pinned={"BalanceControlService": {"acknowledgedVersion": 2, "reason": "done"}}),
        )
        self.assertEqual([finding.kind for finding in findings], [coverage.STALE])

    def test_pin_entry_for_an_uncatalogued_spec_is_reported(self) -> None:
        findings = coverage.evaluate(
            {"GhostService": [1]},
            [],
            baseline(
                uncovered={"GhostService": {"reason": "excluded"}},
                pinned={"GhostService": {"acknowledgedVersion": 1, "reason": "stale"}},
            ),
        )
        self.assertIn(coverage.STALE, [finding.kind for finding in findings])


class TestBaselineValidation(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.path = Path(self.temp_dir.name) / "baseline.json"

    def load(self, content: dict) -> dict:
        self.path.write_text(json.dumps(content))
        return coverage.load_baseline(self.path)

    def test_absent_file_is_an_empty_baseline(self) -> None:
        self.assertEqual(coverage.load_baseline(self.path / "absent"), EMPTY_BASELINE)

    def test_unknown_section_and_fields_are_rejected(self) -> None:
        for content in (
            {"uncoveredSpecs": {}, "somethingElse": {}},
            {"uncoveredSpecs": {"AccountService": {"reason": "ok", "why": "no"}}},
        ):
            with self.subTest(content=content), self.assertRaises(coverage.BaselineError):
                self.load(content)

    def test_entries_require_a_reason(self) -> None:
        for entry in ({}, {"reason": ""}, {"reason": "   "}, {"reason": None}):
            with self.subTest(entry=entry), self.assertRaises(coverage.BaselineError):
                self.load({"uncoveredSpecs": {"AccountService": entry}})

    def test_pin_requires_a_positive_integer_version(self) -> None:
        for version in (None, "2", 0, -1, True, 2.0):
            with self.subTest(version=version), self.assertRaises(coverage.BaselineError):
                self.load({"pinnedVersions": {"S": {"acknowledgedVersion": version, "reason": "ok"}}})

    def test_ticket_is_optional_and_included_in_finding_note(self) -> None:
        loaded = self.load({"uncoveredSpecs": {"S": {"reason": "planned", "ticket": "SDK-1"}}})
        self.assertEqual(loaded["uncoveredSpecs"]["S"]["ticket"], "SDK-1")
        finding = coverage.evaluate({"S": [1]}, [], loaded)[0]
        self.assertEqual(finding.note, "planned (SDK-1)")

    def test_committed_baseline_is_valid(self) -> None:
        self.assertTrue(REPO_BASELINE.exists(), f"{REPO_BASELINE} is missing")
        coverage.load_baseline(REPO_BASELINE)


if __name__ == "__main__":
    unittest.main(verbosity=2)
