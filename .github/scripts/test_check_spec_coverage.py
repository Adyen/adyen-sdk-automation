#!/usr/bin/env python3

"""Tests for check_spec_coverage.py, the guard against silent spec/SDK drift.

The check is only worth having if it fires on genuinely new drift and stays
quiet on gaps that were reviewed, so those two behaviours carry most of the
tests. The baseline validation is covered as well: an entry without a reason,
or one accepting a version that is no longer the newest, would turn the check
into a permanent mute, which is the exact failure mode it exists to prevent.
"""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

import check_spec_coverage as checker

REPO_BASELINE = Path(__file__).parents[2] / "config" / "spec-coverage-baseline.json"

EMPTY_BASELINE = {"uncoveredSpecs": {}, "pinnedVersions": {}}


def baseline(uncovered: dict | None = None, pinned: dict | None = None) -> dict:
    return {"uncoveredSpecs": uncovered or {}, "pinnedVersions": pinned or {}}


def run_quietly(argv: list[str]) -> int:
    """Invoke the check in-process, keeping its report out of the test output."""
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return checker.main(argv)


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
            checker.discover_specs(self.specs_dir),
            {"CheckoutService": [71, 72], "PaymentService": [68]},
        )

    def test_unversioned_files_are_ignored(self) -> None:
        # The spec repo also ships files such as README.md; only <Name>-v<N>.json is a spec.
        self.write("CheckoutService-v72.json", "openapi.json", "CheckoutService.json")
        self.assertEqual(checker.discover_specs(self.specs_dir), {"CheckoutService": [72]})

    def test_missing_directory_is_reported(self) -> None:
        with self.assertRaises(FileNotFoundError):
            checker.discover_specs(self.specs_dir / "absent")

    def test_empty_directory_is_reported(self) -> None:
        # An empty schema/ means the clone failed; reporting zero drift would be a false pass.
        with self.assertRaises(FileNotFoundError):
            checker.discover_specs(self.specs_dir)


class TestSpecName(unittest.TestCase):
    def test_defaults_to_name_service(self) -> None:
        self.assertEqual(checker.spec_name({"name": "Checkout", "version": 72}), "CheckoutService")

    def test_explicit_spec_wins(self) -> None:
        self.assertEqual(
            checker.spec_name({"name": "Transfers", "spec": "TransferService", "version": 4}),
            "TransferService",
        )


class TestUncoveredSpecs(unittest.TestCase):
    def test_spec_without_catalog_entry_is_reported(self) -> None:
        findings = checker.evaluate(
            {"CheckoutService": [72], "ForeignExchangeService": [1]},
            [{"name": "Checkout", "version": 72}],
            EMPTY_BASELINE,
        )
        self.assertEqual([(finding.kind, finding.spec, finding.accepted) for finding in findings],
                         [(checker.UNCOVERED, "ForeignExchangeService", False)])

    def test_baselined_spec_is_accepted(self) -> None:
        findings = checker.evaluate(
            {"CheckoutService": [72], "AccountService": [6]},
            [{"name": "Checkout", "version": 72}],
            baseline(uncovered={"AccountService": {"reason": "Classic Platforms"}}),
        )
        self.assertEqual([finding.accepted for finding in findings], [True])

    def test_baselined_spec_stays_accepted_when_a_new_version_appears(self) -> None:
        # A permanently excluded API keeps receiving spec releases; that must not reopen the finding.
        findings = checker.evaluate(
            {"AccountService": [3, 4, 5, 6, 7]},
            [],
            baseline(uncovered={"AccountService": {"reason": "Classic Platforms"}}),
        )
        self.assertEqual([finding.accepted for finding in findings], [True])

    def test_covered_spec_produces_no_finding(self) -> None:
        findings = checker.evaluate(
            {"CheckoutService": [71, 72]},
            [{"name": "Checkout", "version": 72}],
            EMPTY_BASELINE,
        )
        self.assertEqual(findings, [])


class TestOutdatedVersions(unittest.TestCase):
    def test_catalog_behind_newest_spec_is_reported(self) -> None:
        findings = checker.evaluate(
            {"BalanceControlService": [1, 2]},
            [{"name": "BalanceControl", "version": 1}],
            EMPTY_BASELINE,
        )
        self.assertEqual([(finding.kind, finding.accepted) for finding in findings],
                         [(checker.BEHIND, False)])
        self.assertIn("v1", findings[0].detail)
        self.assertIn("v2", findings[0].detail)

    def test_pin_acknowledged_for_the_newest_version_is_accepted(self) -> None:
        findings = checker.evaluate(
            {"BalanceControlService": [1, 2]},
            [{"name": "BalanceControl", "version": 1}],
            baseline(pinned={"BalanceControlService": {"acknowledgedVersion": 2, "reason": "breaking"}}),
        )
        self.assertEqual([finding.accepted for finding in findings], [True])

    def test_pin_acknowledged_for_an_older_version_fires_again(self) -> None:
        # This is the property that keeps the baseline from muting the next release.
        findings = checker.evaluate(
            {"BalanceControlService": [1, 2, 3]},
            [{"name": "BalanceControl", "version": 1}],
            baseline(pinned={"BalanceControlService": {"acknowledgedVersion": 2, "reason": "breaking"}}),
        )
        self.assertEqual([(finding.kind, finding.accepted) for finding in findings],
                         [(checker.BEHIND, False)])

    def test_catalog_ahead_of_the_specs_is_reported_as_missing(self) -> None:
        findings = checker.evaluate(
            {"CheckoutService": [72]},
            [{"name": "Checkout", "version": 73}],
            EMPTY_BASELINE,
        )
        self.assertEqual([(finding.kind, finding.accepted) for finding in findings],
                         [(checker.MISSING, False)])

    def test_missing_spec_cannot_be_accepted_by_the_baseline(self) -> None:
        # Generation fails at configuration time for a pinned spec that does not exist,
        # so no recorded decision may silence it.
        findings = checker.evaluate(
            {"CheckoutService": [72]},
            [{"name": "Checkout", "version": 73}],
            baseline(
                uncovered={"CheckoutService": {"reason": "irrelevant"}},
                pinned={"CheckoutService": {"acknowledgedVersion": 72, "reason": "irrelevant"}},
            ),
        )
        self.assertIn(checker.MISSING, [finding.kind for finding in findings])
        self.assertFalse(next(finding for finding in findings if finding.kind == checker.MISSING).accepted)


class TestStaleBaseline(unittest.TestCase):
    def test_uncovered_entry_for_a_covered_spec_is_reported(self) -> None:
        findings = checker.evaluate(
            {"CheckoutService": [72]},
            [{"name": "Checkout", "version": 72}],
            baseline(uncovered={"CheckoutService": {"reason": "stale"}}),
        )
        self.assertEqual([(finding.kind, finding.accepted) for finding in findings],
                         [(checker.STALE, False)])

    def test_uncovered_entry_for_an_unpublished_spec_is_reported(self) -> None:
        findings = checker.evaluate(
            {"CheckoutService": [72]},
            [{"name": "Checkout", "version": 72}],
            baseline(uncovered={"RemovedService": {"reason": "stale"}}),
        )
        self.assertEqual([finding.kind for finding in findings], [checker.STALE])

    def test_pin_entry_that_is_no_longer_behind_is_reported(self) -> None:
        findings = checker.evaluate(
            {"BalanceControlService": [1, 2]},
            [{"name": "BalanceControl", "version": 2}],
            baseline(pinned={"BalanceControlService": {"acknowledgedVersion": 2, "reason": "done"}}),
        )
        self.assertEqual([finding.kind for finding in findings], [checker.STALE])

    def test_pin_entry_for_an_uncatalogued_spec_is_reported(self) -> None:
        findings = checker.evaluate(
            {"GhostService": [1]},
            [],
            baseline(
                uncovered={"GhostService": {"reason": "excluded"}},
                pinned={"GhostService": {"acknowledgedVersion": 1, "reason": "stale"}},
            ),
        )
        self.assertIn(checker.STALE, [finding.kind for finding in findings])


class TestBaselineValidation(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.path = Path(self.temp_dir.name) / "baseline.json"

    def load(self, content: dict) -> dict:
        self.path.write_text(json.dumps(content))
        return checker.load_baseline(self.path)

    def test_absent_file_is_an_empty_baseline(self) -> None:
        self.assertEqual(checker.load_baseline(self.path / "absent"), EMPTY_BASELINE)

    def test_unknown_section_is_rejected(self) -> None:
        with self.assertRaises(checker.BaselineError):
            self.load({"uncoveredSpecs": {}, "somethingElse": {}})

    def test_unknown_entry_field_is_rejected(self) -> None:
        with self.assertRaises(checker.BaselineError):
            self.load({"uncoveredSpecs": {"AccountService": {"reason": "ok", "why": "no"}}})

    def test_entry_without_a_reason_is_rejected(self) -> None:
        for entry in ({}, {"reason": ""}, {"reason": "   "}, {"reason": None}):
            with self.subTest(entry=entry), self.assertRaises(checker.BaselineError):
                self.load({"uncoveredSpecs": {"AccountService": entry}})

    def test_pin_without_a_positive_int_version_is_rejected(self) -> None:
        for version in (None, "2", 0, -1, True, 2.0):
            with self.subTest(version=version), self.assertRaises(checker.BaselineError):
                self.load({"pinnedVersions": {"S": {"acknowledgedVersion": version, "reason": "ok"}}})

    def test_ticket_is_optional_and_shown_with_the_reason(self) -> None:
        loaded = self.load({"uncoveredSpecs": {"S": {"reason": "planned", "ticket": "SDK-1"}}})
        self.assertEqual(loaded["uncoveredSpecs"]["S"]["ticket"], "SDK-1")
        finding = checker.evaluate({"S": [1]}, [], loaded)[0]
        self.assertEqual(finding.note, "planned (SDK-1)")


class TestRepositoryBaseline(unittest.TestCase):
    """The committed baseline must stay loadable; a malformed one fails the check with exit 2."""

    def test_committed_baseline_is_valid(self) -> None:
        self.assertTrue(REPO_BASELINE.exists(), f"{REPO_BASELINE} is missing")
        checker.load_baseline(REPO_BASELINE)


class TestReportingAndExitCodes(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.specs_dir = self.root / "json"
        self.specs_dir.mkdir()
        (self.specs_dir / "CheckoutService-v72.json").write_text("{}")
        (self.specs_dir / "ForeignExchangeService-v1.json").write_text("{}")

        self.catalog = self.root / "services.json"
        self.catalog.write_text(json.dumps({"services": [{"name": "Checkout", "version": 72}]}))
        self.baseline_path = self.root / "baseline.json"

    def run_main(self, *extra: str) -> int:
        return run_quietly(
            [
                "--catalog", str(self.catalog),
                "--specs", str(self.specs_dir),
                "--baseline", str(self.baseline_path),
                *extra,
            ]
        )

    def test_unreviewed_drift_exits_one(self) -> None:
        self.assertEqual(self.run_main(), 1)

    def test_accepted_drift_exits_zero(self) -> None:
        self.baseline_path.write_text(
            json.dumps(baseline(uncovered={"ForeignExchangeService": {"reason": "planned"}}))
        )
        self.assertEqual(self.run_main(), 0)

    def test_malformed_baseline_exits_two(self) -> None:
        self.baseline_path.write_text(json.dumps({"uncoveredSpecs": {"S": {}}}))
        self.assertEqual(self.run_main(), 2)

    def test_missing_specs_directory_exits_two(self) -> None:
        self.assertEqual(
            run_quietly(["--catalog", str(self.catalog), "--specs", str(self.root / "absent")]),
            2,
        )

    def test_summary_is_appended_as_markdown(self) -> None:
        summary = self.root / "summary.md"
        summary.write_text("previous content\n")
        self.run_main("--summary", str(summary))
        content = summary.read_text()
        self.assertIn("previous content", content)
        self.assertIn("## SDK spec coverage", content)
        self.assertIn("ForeignExchangeService", content)

    def test_write_baseline_accepts_current_gaps(self) -> None:
        self.assertEqual(self.run_main("--write-baseline"), 0)
        written = json.loads(self.baseline_path.read_text())
        self.assertEqual(written["uncoveredSpecs"]["ForeignExchangeService"]["reason"], checker.UNREVIEWED_REASON)
        # The rewritten baseline must satisfy the validation the check applies on the next run.
        self.assertEqual(self.run_main(), 0)

    def test_write_baseline_keeps_recorded_reasons(self) -> None:
        self.baseline_path.write_text(
            json.dumps(baseline(uncovered={"ForeignExchangeService": {"reason": "planned", "ticket": "SDK-1"}}))
        )
        self.run_main("--write-baseline")
        written = json.loads(self.baseline_path.read_text())
        self.assertEqual(written["uncoveredSpecs"]["ForeignExchangeService"],
                         {"reason": "planned", "ticket": "SDK-1"})

    def test_write_baseline_drops_resolved_gaps(self) -> None:
        self.catalog.write_text(
            json.dumps({"services": [
                {"name": "Checkout", "version": 72},
                {"name": "ForeignExchange", "version": 1},
            ]})
        )
        self.baseline_path.write_text(
            json.dumps(baseline(uncovered={"ForeignExchangeService": {"reason": "planned"}}))
        )
        self.run_main("--write-baseline")
        self.assertEqual(json.loads(self.baseline_path.read_text()), EMPTY_BASELINE)


class TestBaselineOrdering(unittest.TestCase):
    """The committed baseline is grouped by theme, so rewriting it must not reorder it."""

    def build(self, specs: dict[str, list[int]], previous: dict) -> dict:
        return checker.build_baseline(checker.evaluate(specs, [], previous), specs, previous)

    def test_recorded_entries_keep_their_order(self) -> None:
        specs = {"AService": [1], "BService": [1], "CService": [1]}
        previous = baseline(uncovered={
            "CService": {"reason": "hand-grouped first"},
            "AService": {"reason": "second"},
            "BService": {"reason": "third"},
        })
        self.assertEqual(list(self.build(specs, previous)["uncoveredSpecs"]), ["CService", "AService", "BService"])

    def test_new_entries_are_appended_after_the_recorded_ones(self) -> None:
        specs = {"AService": [1], "ZService": [1]}
        previous = baseline(uncovered={"ZService": {"reason": "recorded"}})
        self.assertEqual(list(self.build(specs, previous)["uncoveredSpecs"]), ["ZService", "AService"])

    def test_rewriting_an_unchanged_baseline_is_a_no_op(self) -> None:
        specs = {"AService": [1], "BService": [2]}
        previous = baseline(
            uncovered={"BService": {"reason": "second by hand"}, "AService": {"reason": "first by hand"}}
        )
        self.assertEqual(self.build(specs, previous), previous)


if __name__ == "__main__":
    unittest.main(verbosity=2)
