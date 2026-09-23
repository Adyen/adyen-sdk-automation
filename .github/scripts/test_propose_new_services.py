#!/usr/bin/env python3

"""Tests for propose_new_services.py.

The script writes to the catalog that every Gradle invocation and the CI matrix
read, so two properties carry most of the tests: the edit must leave the rest of
the hand-formatted file untouched, and the result must satisfy the validation in
test_services_catalog.py. A proposal that fails that validation would break
generation at configuration time for every library.
"""

import contextlib
import io
import json
import re
import tempfile
import unittest
from pathlib import Path

import check_spec_coverage as checker
import propose_new_services as proposer

CATALOG_TEXT = """{
  "services": [
    { "name": "Checkout", "version": 72, "group": "Payments" },
    { "name": "Payout", "version": 68, "group": "Payments" },

    { "name": "Transfers", "spec": "TransferService", "version": 4, "group": "Adyen for Platforms" }
  ]
}
"""


def catalog_services(text: str) -> list[dict]:
    return json.loads(text)["services"]


class TestDeriveName(unittest.TestCase):
    def test_service_suffix_is_dropped(self) -> None:
        self.assertEqual(proposer.derive_name("ForeignExchangeService"), "ForeignExchange")

    def test_notification_becomes_webhooks_without_the_platform_prefix(self) -> None:
        self.assertEqual(
            proposer.derive_name("BalancePlatformAccountingNotification"), "AccountingWebhooks"
        )

    def test_notification_without_the_platform_prefix(self) -> None:
        self.assertEqual(proposer.derive_name("TokenizationNotification"), "TokenizationWebhooks")

    def test_notification_service_becomes_webhooks(self) -> None:
        # Precedent: ManagementNotificationService is ManagementWebhooks, not ManagementNotificationWebhooks.
        self.assertEqual(proposer.derive_name("ManagementNotificationService"), "ManagementWebhooks")

    def test_unrecognised_shape_is_kept_verbatim(self) -> None:
        self.assertEqual(proposer.derive_name("Webhooks"), "Webhooks")

    def test_derived_names_reproduce_catalog_precedent_where_a_rule_exists(self) -> None:
        for spec, expected in (
            ("CheckoutService", "Checkout"),
            ("PaymentsAppService", "PaymentsApp"),
            ("BalancePlatformAcsNotification", "AcsWebhooks"),
            ("BalancePlatformConfigurationNotification", "ConfigurationWebhooks"),
            ("BalancePlatformTransferNotification", "TransferWebhooks"),
        ):
            with self.subTest(spec=spec):
                self.assertEqual(proposer.derive_name(spec), expected)


class TestNameFromTitle(unittest.TestCase):
    def test_adyen_prefix_is_dropped(self) -> None:
        self.assertEqual(proposer.name_from_title("Adyen Checkout API"), "Checkout")

    def test_api_suffix_is_dropped(self) -> None:
        self.assertEqual(proposer.name_from_title("Legal Entity Management API"), "LegalEntityManagement")

    def test_singular_webhook_is_pluralised(self) -> None:
        self.assertEqual(proposer.name_from_title("Balance webhook"), "BalanceWebhooks")

    def test_deprecation_marker_is_dropped(self) -> None:
        self.assertEqual(proposer.name_from_title("POS Terminal Management API (deprecated)"), "POSTerminalManagement")

    def test_punctuation_is_stripped(self) -> None:
        self.assertEqual(
            proposer.name_from_title("Account-to-Account (A2A) payments API"), "AccountToAccountA2APayments"
        )

    def test_reproduces_catalog_precedent(self) -> None:
        for title, expected in (
            ("Adyen Payout API", "Payout"),
            ("Document Collector API", "DocumentCollector"),
            ("Session authentication API", "SessionAuthentication"),
            ("Tokenization webhooks", "TokenizationWebhooks"),
            ("Management Webhooks", "ManagementWebhooks"),
        ):
            with self.subTest(title=title):
                self.assertEqual(proposer.name_from_title(title), expected)


class TestCandidateNames(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.specs_dir = Path(self.temp_dir.name)

    def write_spec(self, filename: str, info: dict) -> None:
        (self.specs_dir / filename).write_text(json.dumps({"info": info}))

    def test_agreeing_rules_yield_no_alternative(self) -> None:
        self.write_spec("ForeignExchangeService-v1.json", {"title": "Foreign Exchange API"})
        self.assertEqual(
            proposer.candidate_names(self.specs_dir, "ForeignExchangeService", 1), ("ForeignExchange", "")
        )

    def test_disagreeing_rules_keep_the_filename_name_as_alternative(self) -> None:
        self.write_spec("A2APaymentsService-v1.json", {"title": "Account-to-Account (A2A) payments API"})
        self.assertEqual(
            proposer.candidate_names(self.specs_dir, "A2APaymentsService", 1),
            ("AccountToAccountA2APayments", "A2APayments"),
        )

    def test_missing_spec_file_falls_back_to_the_filename_rule(self) -> None:
        self.assertEqual(proposer.candidate_names(self.specs_dir, "WalletService", 1), ("Wallet", ""))

    def test_unparsable_spec_falls_back_to_the_filename_rule(self) -> None:
        (self.specs_dir / "WalletService-v1.json").write_text("not json")
        self.assertEqual(proposer.candidate_names(self.specs_dir, "WalletService", 1), ("Wallet", ""))

    def test_unusable_title_falls_back_to_the_filename_rule(self) -> None:
        self.write_spec("WalletService-v1.json", {"title": "2025 API"})
        self.assertEqual(proposer.candidate_names(self.specs_dir, "WalletService", 1), ("Wallet", ""))


class TestPublicVersion(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.specs_dir = Path(self.temp_dir.name)

    def write(self, spec: str, version: int, info: dict) -> None:
        (self.specs_dir / f"{spec}-v{version}.json").write_text(json.dumps({"info": info}))

    def test_newest_version_wins_when_nothing_is_marked(self) -> None:
        # x-publicVersion is absent from 21 published specs, so absence must not exclude.
        self.write("S", 1, {})
        self.write("S", 2, {})
        self.assertEqual(proposer.public_version(self.specs_dir, "S", [1, 2]), 2)

    def test_explicitly_non_public_version_is_skipped(self) -> None:
        self.write("S", 1, {"x-publicVersion": True})
        self.write("S", 2, {"x-publicVersion": False})
        self.assertEqual(proposer.public_version(self.specs_dir, "S", [1, 2]), 1)

    def test_all_versions_non_public_falls_back_to_the_newest(self) -> None:
        self.write("S", 1, {"x-publicVersion": False})
        self.assertEqual(proposer.public_version(self.specs_dir, "S", [1]), 1)


class TestBuildPlan(unittest.TestCase):
    def setUp(self) -> None:
        self.services = [{"name": "Checkout", "version": 72}]
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.specs_dir = Path(self.temp_dir.name)

    def plan_for(self, specs: dict[str, list[int]], baseline: dict | None = None) -> proposer.Plan:
        baseline = baseline or {"uncoveredSpecs": {}, "pinnedVersions": {}}
        findings = checker.evaluate(specs, self.services, baseline)
        return proposer.build_plan(findings, specs, self.services, self.specs_dir)

    def test_uncovered_spec_becomes_a_proposal_at_its_newest_version(self) -> None:
        plan = self.plan_for({"CheckoutService": [72], "ForeignExchangeService": [1, 2]})
        self.assertEqual(len(plan.proposals), 1)
        self.assertEqual((plan.proposals[0].name, plan.proposals[0].version), ("ForeignExchange", 2))

    def test_baselined_spec_is_never_proposed(self) -> None:
        # A recorded decision means hands off; removing the entry is how you ask for a proposal.
        plan = self.plan_for(
            {"CheckoutService": [72], "AccountService": [6]},
            {"uncoveredSpecs": {"AccountService": {"reason": "Classic Platforms"}}, "pinnedVersions": {}},
        )
        self.assertEqual(plan.proposals, [])
        self.assertEqual(plan.skipped, [])

    def test_version_lag_is_out_of_scope(self) -> None:
        plan = self.plan_for({"CheckoutService": [72, 73]})
        self.assertEqual(plan.proposals, [])

    def test_colliding_name_is_skipped_with_a_reason(self) -> None:
        # CheckoutService is covered, so a second spec deriving to Checkout must not
        # produce a duplicate service id, which test_services_catalog.py rejects.
        plan = self.plan_for({"CheckoutService": [72], "Checkout": [1]})
        self.assertEqual(plan.proposals, [])
        self.assertEqual(len(plan.skipped), 1)
        self.assertIn("collides", plan.skipped[0][1])

    def test_two_specs_deriving_to_the_same_name_only_propose_once(self) -> None:
        plan = self.plan_for({"WalletService": [1], "WalletNotificationService": [1], "Wallet": [1]})
        names = [proposal.name for proposal in plan.proposals]
        self.assertEqual(len(names), len(set(names)))
        self.assertTrue(plan.skipped)

    def test_non_alphanumeric_name_is_skipped(self) -> None:
        plan = self.plan_for({"CheckoutService": [72], "Foo-Bar": [1]})
        self.assertEqual(plan.proposals, [])
        self.assertIn("alphanumeric", plan.skipped[0][1])


class TestProposalEntry(unittest.TestCase):
    def test_spec_is_omitted_when_gradle_can_derive_it(self) -> None:
        proposal = proposer.Proposal(spec="ForeignExchangeService", name="ForeignExchange", version=1)
        self.assertEqual(proposal.entry, {"name": "ForeignExchange", "version": 1})
        self.assertNotIn("spec", proposal.line)

    def test_spec_is_included_when_it_differs(self) -> None:
        proposal = proposer.Proposal(spec="TokenizationNotification", name="TokenizationWebhooks", version=1)
        self.assertEqual(
            proposal.entry,
            {"name": "TokenizationWebhooks", "spec": "TokenizationNotification", "version": 1},
        )

    def test_line_matches_the_catalog_style(self) -> None:
        proposal = proposer.Proposal(spec="ForeignExchangeService", name="ForeignExchange", version=1)
        self.assertEqual(proposal.line, '    { "name": "ForeignExchange", "version": 1 }')


class TestInsertEntries(unittest.TestCase):
    def proposals(self, *pairs: tuple[str, str, int]) -> list[proposer.Proposal]:
        return [proposer.Proposal(spec=spec, name=name, version=version) for spec, name, version in pairs]

    def test_no_proposals_leaves_the_text_untouched(self) -> None:
        self.assertEqual(proposer.insert_entries(CATALOG_TEXT, []), CATALOG_TEXT)

    def test_existing_lines_are_unchanged_except_the_added_comma(self) -> None:
        result = proposer.insert_entries(CATALOG_TEXT, self.proposals(("ForeignExchangeService", "ForeignExchange", 1)))
        before = CATALOG_TEXT.split("\n")
        after = result.split("\n")
        changed = [line for line in before if line not in after]
        self.assertEqual(
            changed,
            ['    { "name": "Transfers", "spec": "TransferService", "version": 4, "group": "Adyen for Platforms" }'],
        )
        self.assertIn(changed[0] + ",", after)

    def test_result_is_valid_json_with_the_new_entry(self) -> None:
        result = proposer.insert_entries(CATALOG_TEXT, self.proposals(("ForeignExchangeService", "ForeignExchange", 1)))
        services = catalog_services(result)
        self.assertEqual(len(services), 4)
        self.assertEqual(services[-1], {"name": "ForeignExchange", "version": 1})

    def test_multiple_proposals_are_comma_separated(self) -> None:
        result = proposer.insert_entries(
            CATALOG_TEXT,
            self.proposals(("ForeignExchangeService", "ForeignExchange", 1), ("WalletService", "Wallet", 2)),
        )
        services = catalog_services(result)
        self.assertEqual([service["name"] for service in services[-2:]], ["ForeignExchange", "Wallet"])

    def test_trailing_newline_is_preserved(self) -> None:
        result = proposer.insert_entries(CATALOG_TEXT, self.proposals(("WalletService", "Wallet", 1)))
        self.assertTrue(result.endswith("\n"))
        self.assertFalse(result.endswith("\n\n"))

    def test_applying_twice_is_stable(self) -> None:
        once = proposer.insert_entries(CATALOG_TEXT, self.proposals(("WalletService", "Wallet", 1)))
        twice = proposer.insert_entries(once, [])
        self.assertEqual(once, twice)

    def test_malformed_catalog_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            proposer.insert_entries('{"services": []}', self.proposals(("WalletService", "Wallet", 1)))


class TestProposalsSatisfyCatalogValidation(unittest.TestCase):
    """A proposal that the catalog test rejects would break generation for every library."""

    def test_written_entries_pass_the_catalog_rules(self) -> None:
        proposals = [
            proposer.Proposal(spec="ForeignExchangeService", name="ForeignExchange", version=1),
            proposer.Proposal(spec="BalancePlatformAccountingNotification", name="AccountingWebhooks", version=3),
        ]
        services = catalog_services(proposer.insert_entries(CATALOG_TEXT, proposals))

        supported = {"name", "version", "spec", "small", "group", "projects", "excludedProjects"}
        ids = [service["name"].lower() for service in services]
        self.assertEqual(len(ids), len(set(ids)), "service ids must be unique")
        for service in services:
            with self.subTest(service=service["name"]):
                self.assertEqual(set(service) - supported, set())
                self.assertRegex(service["name"], r"^[A-Za-z][A-Za-z0-9]*$")
                self.assertIsInstance(service["version"], int)
                self.assertNotIsInstance(service["version"], bool)
                self.assertGreater(service["version"], 0)


class TestPullRequestBody(unittest.TestCase):
    def test_body_lists_the_proposal_and_warns_about_the_name(self) -> None:
        plan = proposer.Plan(
            proposals=[proposer.Proposal(spec="ForeignExchangeService", name="ForeignExchange", version=1)]
        )
        body = proposer.render_pr_body(plan)
        self.assertIn("`ForeignExchange`", body)
        self.assertIn("ForeignExchangeService-v1.json", body)
        self.assertIn("**Every `name` is a guess.**", body)
        self.assertIn("spec-coverage-baseline.json", body)
        self.assertIn("- [ ]", body)

    def test_body_shows_the_alternative_name_when_the_rules_disagree(self) -> None:
        plan = proposer.Plan(
            proposals=[
                proposer.Proposal(
                    spec="A2APaymentsService",
                    name="AccountToAccountA2APayments",
                    version=1,
                    alternative="A2APayments",
                )
            ]
        )
        body = proposer.render_pr_body(plan)
        self.assertIn("`AccountToAccountA2APayments`", body)
        self.assertIn("`A2APayments`", body)

    def test_body_lists_skipped_specs(self) -> None:
        body = proposer.render_pr_body(proposer.Plan(skipped=[("Checkout", "derived name collides")]))
        self.assertIn("Needs a name chosen by hand", body)
        self.assertIn("`Checkout`", body)

    def test_empty_plan_says_so(self) -> None:
        self.assertIn("No published spec is missing", proposer.render_pr_body(proposer.Plan()))


class TestMain(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)

        self.specs_dir = self.root / "json"
        self.specs_dir.mkdir()
        for filename in ("CheckoutService-v72.json", "ForeignExchangeService-v1.json"):
            (self.specs_dir / filename).write_text("{}")

        self.catalog = self.root / "services.json"
        self.catalog.write_text(CATALOG_TEXT)
        self.baseline = self.root / "baseline.json"
        self.baseline.write_text(json.dumps({"uncoveredSpecs": {}, "pinnedVersions": {}}))

    def run_main(self, *extra: str) -> int:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return proposer.main(
                [
                    "--catalog", str(self.catalog),
                    "--specs", str(self.specs_dir),
                    "--baseline", str(self.baseline),
                    *extra,
                ]
            )

    def test_dry_run_does_not_touch_the_catalog(self) -> None:
        self.assertEqual(self.run_main(), 0)
        self.assertEqual(self.catalog.read_text(), CATALOG_TEXT)

    def test_write_adds_the_entry(self) -> None:
        self.assertEqual(self.run_main("--write"), 0)
        names = [service["name"] for service in catalog_services(self.catalog.read_text())]
        self.assertIn("ForeignExchange", names)

    def test_write_is_idempotent(self) -> None:
        self.run_main("--write")
        first = self.catalog.read_text()
        self.run_main("--write")
        self.assertEqual(self.catalog.read_text(), first)

    def test_write_is_a_no_op_once_the_spec_is_baselined(self) -> None:
        self.baseline.write_text(
            json.dumps({"uncoveredSpecs": {"ForeignExchangeService": {"reason": "planned"}}, "pinnedVersions": {}})
        )
        self.run_main("--write")
        self.assertEqual(self.catalog.read_text(), CATALOG_TEXT)

    def test_pr_body_is_written(self) -> None:
        body = self.root / "body.md"
        self.run_main("--pr-body", str(body))
        self.assertIn("ForeignExchange", body.read_text())

    def test_missing_specs_directory_exits_two(self) -> None:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            code = proposer.main(["--catalog", str(self.catalog), "--specs", str(self.root / "absent")])
        self.assertEqual(code, 2)

    def test_written_catalog_keeps_the_original_formatting(self) -> None:
        self.run_main("--write")
        lines = self.catalog.read_text().split("\n")
        # Every entry stays on one line at four-space indentation.
        entries = [line for line in lines if line.strip().startswith('{ "name"')]
        self.assertEqual(len(entries), 4)
        for line in entries:
            with self.subTest(line=line):
                self.assertRegex(line, r"^ {4}\{ \"name\": ")
                self.assertIsNotNone(re.search(r"\}(,)?$", line))


if __name__ == "__main__":
    unittest.main(verbosity=2)
