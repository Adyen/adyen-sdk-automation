#!/usr/bin/env python3

import contextlib
import io
import json
import os
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError
from unittest import mock

import sdk_coverage


class TestCheckFormatPrerequisites(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_project_without_prerequisites(self) -> None:
        self.assertTrue(
            sdk_coverage.check_format_prerequisites(
                "java"
            )
        )

    def test_unresolvable_command_fails_with_hint(
            self,
    ) -> None:
        # No commands resolve on this PATH, and Go is
        # not available to bootstrap anything.
        empty = self.root / "empty"
        empty.mkdir()

        with mock.patch.dict(
            os.environ,
            {"PATH": str(empty)},
        ):
            with contextlib.redirect_stdout(
                io.StringIO()
            ) as output:
                result = (
                    sdk_coverage
                    .check_format_prerequisites(
                        "go"
                    )
                )

        self.assertFalse(result)
        self.assertIn(
            "goimports is not on PATH",
            output.getvalue(),
        )
        self.assertIn(
            "Install Go",
            output.getvalue(),
        )

    def test_installed_command_off_path_fails(
            self,
    ) -> None:
        # goimports is installed in the Go bin
        # directory, which is missing from PATH.
        stub_dir = self.root / "stub"
        stub_dir.mkdir()
        go_stub = stub_dir / "go"
        go_stub.write_text(
            "#!/bin/sh\n"
            f"echo {self.root / 'gopath'}\n"
        )
        go_stub.chmod(0o755)

        bin_directory = self.root / "gopath" / "bin"
        bin_directory.mkdir(parents=True)
        (bin_directory / "goimports").write_text(
            "#!/bin/sh\n"
        )

        with mock.patch.dict(
            os.environ,
            {"PATH": str(stub_dir)},
        ):
            with contextlib.redirect_stdout(
                io.StringIO()
            ) as output:
                result = (
                    sdk_coverage
                    .check_format_prerequisites(
                        "go"
                    )
                )

        self.assertFalse(result)
        self.assertIn(
            "is installed at",
            output.getvalue(),
        )
        self.assertIn(
            f'export PATH="{bin_directory}:$PATH"',
            output.getvalue(),
        )

    def test_bootstrap_directory_on_path_passes(
            self,
    ) -> None:
        # goimports is missing, but the Makefile
        # bootstraps it into a directory on PATH.
        stub_dir = self.root / "stub"
        stub_dir.mkdir()
        go_stub = stub_dir / "go"
        go_stub.write_text(
            "#!/bin/sh\n"
            f"echo {self.root / 'gopath'}\n"
        )
        go_stub.chmod(0o755)

        bin_directory = self.root / "gopath" / "bin"
        bin_directory.mkdir(parents=True)

        with mock.patch.dict(
            os.environ,
            {
                "PATH": (
                    f"{stub_dir}"
                    f"{os.pathsep}"
                    f"{bin_directory}"
                ),
            },
        ):
            self.assertTrue(
                sdk_coverage
                .check_format_prerequisites("go")
            )

    def test_resolvable_command_passes(self) -> None:
        stub_dir = self.root / "stub"
        stub_dir.mkdir()
        (stub_dir / "goimports").write_text(
            "#!/bin/sh\n"
        )
        (stub_dir / "goimports").chmod(0o755)

        with mock.patch.dict(
            os.environ,
            {"PATH": str(stub_dir)},
        ):
            self.assertTrue(
                sdk_coverage
                .check_format_prerequisites("go")
            )


class TestFamilyCandidateNames(unittest.TestCase):
    def test_terminal_alias_is_only_valid_for_python(self) -> None:
        for project in sdk_coverage.PROJECTS:
            with self.subTest(project=project):
                names = sdk_coverage.family_candidate_names("TfmAPIService", project)
                self.assertEqual("Terminal" in names, project == "python")

    def test_spec_derived_names(self) -> None:
        self.assertEqual(
            sdk_coverage.family_candidate_names(
                "OpenBankingService",
                "java",
            ),
            ["OpenBankingService", "OpenBanking"],
        )

    def test_family_without_service_suffix(self) -> None:
        self.assertEqual(
            sdk_coverage.family_candidate_names(
                "Webhooks",
                "java",
            ),
            ["Webhooks"],
        )

    def test_alias_names(self) -> None:
        names = sdk_coverage.family_candidate_names(
            "FundService",
            "java",
        )

        self.assertIn("Fund", names)
        self.assertIn("MarketPay", names)
        self.assertIn("PlatformsFund", names)

    def test_marketpay_facade_is_not_notification_evidence(
            self,
    ) -> None:
        # Ruby ships account, fund, notification
        # configuration, and hop services in its
        # MarketPay facade, but no notification payload
        # models.
        for project in sdk_coverage.PROJECTS:
            names = (
                sdk_coverage
                .family_candidate_names(
                    "MarketPayNotificationService",
                    project,
                )
            )

            self.assertNotIn(
                "MarketPay",
                names,
            )

    def test_project_scoped_aliases(self) -> None:
        php_names = (
            sdk_coverage
            .family_candidate_names(
                "NotificationConfigurationService",
                "php",
            )
        )

        java_names = (
            sdk_coverage
            .family_candidate_names(
                "NotificationConfigurationService",
                "java",
            )
        )

        self.assertIn("Notification", php_names)
        self.assertNotIn("Notification", java_names)


class TestTitleNeedles(unittest.TestCase):
    def test_plain_title(self) -> None:
        self.assertEqual(
            sdk_coverage.title_search_needles("Fund API"),
            ["Fund API"],
        )

    def test_parenthetical_title(self) -> None:
        self.assertEqual(
            sdk_coverage.title_search_needles(
                "POS Terminal Management API"
                " (deprecated)"
            ),
            [
                "POS Terminal Management API"
                " (deprecated)",
                "POS Terminal Management API",
            ],
        )

    def test_generic_titles_are_not_searchable(self) -> None:
        self.assertEqual(
            sdk_coverage.searchable_title_needles(
                "Webhooks"
            ),
            [],
        )


class TestResolveExistingPath(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        (self.root / "marketpay.rb").write_text("")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_exact_path(self) -> None:
        self.assertEqual(
            sdk_coverage.resolve_existing_path(
                self.root / "marketpay.rb"
            ),
            self.root / "marketpay.rb",
        )

    def test_casing_is_ignored(self) -> None:
        self.assertEqual(
            sdk_coverage.resolve_existing_path(
                self.root / "MarketPay.rb"
            ),
            self.root / "marketpay.rb",
        )

    def test_missing_path(self) -> None:
        self.assertIsNone(
            sdk_coverage.resolve_existing_path(
                self.root / "FundApi.php"
            )
        )


class TestReadVersionFromSourcePaths(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def write_source(
            self,
            name,
            content,
    ) -> Path:
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

        return path

    def test_dotnet_api_version_marker(self) -> None:
        path = self.write_source(
            "Adyen/Management/ManagementApi.cs",
            'public string ApiVersion => "3";\n',
        )

        self.assertEqual(
            sdk_coverage
            .read_version_from_source_paths(
                [path],
                "dotnet",
            ),
            3,
        )

    def test_dotnet_openapi_document_marker(self) -> None:
        # Management and BalancePlatform files carry the
        # spec version as a banner line instead of an
        # ApiVersion property.
        path = self.write_source(
            "Adyen/Management/Model.cs",
            " * The version of the OpenAPI"
            " document: 3\n",
        )

        self.assertEqual(
            sdk_coverage
            .read_version_from_source_paths(
                [path],
                "dotnet",
            ),
            3,
        )

    def test_disagreeing_markers_have_no_version(
            self,
    ) -> None:
        first = self.write_source(
            "Adyen/Mixed/First.cs",
            'public string ApiVersion => "3";\n',
        )
        second = self.write_source(
            "Adyen/Mixed/Second.cs",
            " * The version of the OpenAPI"
            " document: 4\n",
        )

        self.assertIsNone(
            sdk_coverage
            .read_version_from_source_paths(
                [first, second],
                "dotnet",
            )
        )


class TestParseChangedPaths(unittest.TestCase):
    def test_modified_and_untracked_paths(self) -> None:
        self.assertEqual(
            sdk_coverage.parse_changed_paths(
                [
                    " M src/Adyen/Service/CheckoutApi.php",
                    "?? src/Adyen/Model/TransfersApi.php",
                ]
            ),
            [
                "src/Adyen/Service/CheckoutApi.php",
                "src/Adyen/Model/TransfersApi.php",
            ],
        )

    def test_untracked_directory_loses_its_slash(
            self,
    ) -> None:
        self.assertEqual(
            sdk_coverage.parse_changed_paths(
                ["?? src/Adyen/Model/TransfersApi/"]
            ),
            ["src/Adyen/Model/TransfersApi"],
        )

    def test_deleted_paths_are_dropped(self) -> None:
        self.assertEqual(
            sdk_coverage.parse_changed_paths(
                [
                    "D  src/Adyen/Service/Old.php",
                    " D src/Adyen/Service/Old2.php",
                ]
            ),
            [],
        )

    def test_rename_keeps_the_new_path(self) -> None:
        self.assertEqual(
            sdk_coverage.parse_changed_paths(
                ["R  src/old.php -> src/new.php"]
            ),
            ["src/new.php"],
        )

    def test_quoted_paths(self) -> None:
        self.assertEqual(
            sdk_coverage.parse_changed_paths(
                ['?? "src/odd name.php"']
            ),
            ["src/odd name.php"],
        )


class TestFormatGeneratedCode(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp_dir.name)
        self.commands = []

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def record_command(self, command, cwd):
        self.commands.append(command)

        return mock.Mock(returncode=0)

    def test_php_formats_only_changed_paths(self) -> None:
        with mock.patch.object(
                sdk_coverage,
                "has_format_action",
                return_value=True,
        ):
            with mock.patch.object(
                    sdk_coverage,
                    "run_command",
                    side_effect=self.record_command,
            ):
                result = (
                    sdk_coverage
                    .format_generated_code(
                        self.repo,
                        "php",
                        ["src/Adyen/A.php"],
                    )
                )

        self.assertTrue(result)
        self.assertEqual(
            self.commands,
            [["vendor/bin/phpcbf", "src/Adyen/A.php"]],
        )

    def test_php_without_paths_uses_the_full_script(
            self,
    ) -> None:
        with mock.patch.object(
                sdk_coverage,
                "has_format_action",
                return_value=True,
        ):
            with mock.patch.object(
                    sdk_coverage,
                    "run_command",
                    side_effect=self.record_command,
            ):
                result = (
                    sdk_coverage
                    .format_generated_code(
                        self.repo,
                        "php",
                        None,
                    )
                )

        self.assertTrue(result)
        self.assertEqual(
            self.commands,
            [["composer", "run", "fmt"]],
        )

    def test_other_projects_ignore_paths(self) -> None:
        with mock.patch.object(
                sdk_coverage,
                "has_format_action",
                return_value=True,
        ):
            with mock.patch.object(
                    sdk_coverage,
                    "run_command",
                    side_effect=self.record_command,
            ):
                result = (
                    sdk_coverage
                    .format_generated_code(
                        self.repo,
                        "java",
                        ["src/A.java"],
                    )
                )

        self.assertTrue(result)
        self.assertEqual(
            self.commands,
            [["mvn", "spotless:apply"]],
        )


class TestFindDuplicateFamilies(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

        surface = {
            "paths": {"/ping": {"get": {}}},
            "components": {"schemas": {}},
        }

        for name in ("AlphaService", "BetaService"):
            spec = {
                "openapi": "3.0.0",
                "info": {
                    "title": name,
                    "version": 1,
                },
                "servers": [
                    {"url": f"https://{name}"}
                ],
                **surface,
            }

            (self.root / f"{name}-v1.json").write_text(
                json.dumps(spec)
            )

        distinct = {
            "openapi": "3.0.0",
            "info": {
                "title": "Gamma",
                "version": 2,
            },
            "paths": {"/other": {"post": {}}},
            "components": {},
        }

        (
                self.root
                / "GammaService-v2.json"
        ).write_text(json.dumps(distinct))

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_identical_surfaces_are_duplicates(self) -> None:
        duplicates = sdk_coverage.find_duplicate_families(
            self.root,
            [
                ("AlphaService", 1),
                ("BetaService", 1),
                ("GammaService", 2),
            ],
        )

        self.assertEqual(
            duplicates,
            {
                "AlphaService": "BetaService",
                "BetaService": "AlphaService",
            },
        )


class TestDetectSdkFamilies(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp_dir.name)
        self.service_dir = (
                self.repo
                / "src/main/java"
                / "com/adyen/service"
        )
        self.service_dir.mkdir(parents=True)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def write_service_file(
            self,
            directory,
            file_name,
            title,
            version,
    ) -> None:
        content = (
            "/*\n"
            f" * {title}\n"
            " *\n"
            f" * The version of the OpenAPI"
            f" document: {version}\n"
            " */\n"
        )

        path = directory / file_name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    def test_generated_family_is_detected(self) -> None:
        self.write_service_file(
            self.service_dir,
            "AccountVerificationApi.java",
            "Open Banking API",
            1,
        )

        self.write_service_file(
            self.service_dir / "openbanking",
            "AccountVerificationApi.java",
            "Open Banking API",
            1,
        )

        findings = sdk_coverage.detect_sdk_families(
            self.repo,
            "java",
            [
                "OpenBankingService",
                "FundService",
                "Webhooks",
            ],
            {
                "OpenBankingService": "Open Banking API",
                "FundService": "Fund API",
                "Webhooks": "Webhooks",
            },
        )

        self.assertEqual(
            findings["OpenBankingService"],
            ("Present", 1),
        )
        self.assertEqual(
            findings["FundService"],
            ("Absent", None),
        )
        self.assertEqual(
            findings["Webhooks"],
            ("Unknown", None),
        )

    def test_title_mentions_without_markers_are_ignored(
            self,
    ) -> None:
        # A bare mention, neither on its own line nor with
        # a version marker, must not report the family.
        (self.service_dir / "Unrelated.java").write_text(
            "package com.adyen.service;\n"
            "// The Fund API is described elsewhere.\n"
        )

        findings = sdk_coverage.detect_sdk_families(
            self.repo,
            "java",
            ["FundService"],
            {"FundService": "Fund API"},
        )

        self.assertEqual(
            findings["FundService"],
            ("Absent", None),
        )

    def test_disagreeing_versions_report_no_version(
            self,
    ) -> None:
        self.write_service_file(
            self.service_dir / "openbanking",
            "FirstApi.java",
            "Open Banking API",
            1,
        )

        self.write_service_file(
            self.service_dir / "openbanking",
            "SecondApi.java",
            "Open Banking API",
            2,
        )

        findings = sdk_coverage.detect_sdk_families(
            self.repo,
            "java",
            ["OpenBankingService"],
            {"OpenBankingService": "Open Banking API"},
        )

        self.assertEqual(
            findings["OpenBankingService"],
            ("Present", None),
        )

    def test_conflicting_title_versions_are_not_overridden_by_a_path_version(self) -> None:
        self.write_service_file(
            self.service_dir / "openbanking", "FirstApi.java", "Open Banking API", 1
        )
        self.write_service_file(
            self.service_dir / "other", "SecondApi.java", "Open Banking API", 2
        )
        findings = sdk_coverage.detect_sdk_families(
            self.repo, "java", ["OpenBankingService"],
            {"OpenBankingService": "Open Banking API"},
        )
        self.assertEqual(findings["OpenBankingService"], ("Present", None))

    def test_hand_written_legacy_service_is_detected(
            self,
    ) -> None:
        # Legacy PHP services live in single files named
        # after the API.
        php_service_dir = (
                self.repo
                / "src/Adyen/Service"
        )
        php_service_dir.mkdir(parents=True)
        (php_service_dir / "Fund.php").write_text(
            "<?php\n"
        )

        findings = sdk_coverage.detect_sdk_families(
            self.repo,
            "php",
            ["FundService"],
            {"FundService": "Fund API"},
        )

        self.assertEqual(
            findings["FundService"],
            ("Present", None),
        )


class TestCoverageInputs(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.schema = self.root / "schema"
        self.schema.mkdir()

    def test_public_version_discovery_matches_the_checker(self) -> None:
        (self.schema / "CheckoutService-v72.json").write_text("{}")
        (self.schema / "CheckoutService-v73.json").write_text(
            json.dumps({"info": {"x-publicVersion": False}})
        )
        self.assertEqual(
            sdk_coverage.discover_openapi_families(self.schema), {"CheckoutService": 72}
        )

    def test_missing_pinned_version_is_reported_even_when_family_exists(self) -> None:
        (self.schema / "CheckoutService-v72.json").write_text("{}")
        service = {"name": "Checkout", "version": 73}
        self.assertEqual(
            sdk_coverage.audit_catalog([service], {"CheckoutService": 72}, self.schema),
            ([], [], [service]),
        )

    def test_missing_historical_version_is_reported(self) -> None:
        (self.schema / "CheckoutService-v72.json").write_text("{}")
        service = {"name": "Checkout", "version": 71}
        self.assertEqual(
            sdk_coverage.audit_catalog([service], {"CheckoutService": 72}, self.schema)[2],
            [service],
        )

    def test_workspace_applies_each_languages_generator_properties(self) -> None:
        source = self.root / "source"
        (source / "buildSrc").mkdir(parents=True)
        (source / "buildSrc/gradle.properties").write_text("openapiGeneratorVersion=7.11.0\n")
        for project in sdk_coverage.PROJECTS:
            (source / project).mkdir()
            properties = sdk_coverage.ROOT / project / "gradle.properties"
            shutil.copyfile(properties, source / project / "gradle.properties")
        (self.schema / "fixture.json").write_text("{}")

        def clone(destination):
            shutil.copytree(source, destination)
            return True

        with mock.patch.object(sdk_coverage, "clone_automation_repo", side_effect=clone):
            for project in sdk_coverage.PROJECTS:
                with self.subTest(project=project):
                    workspace = sdk_coverage.prepare_project_workspace(self.root, self.schema, project)
                    self.assertIsNotNone(workspace)
                    self.assertEqual(
                        (workspace / "buildSrc/gradle.properties").read_text(),
                        (source / project / "gradle.properties").read_text(),
                    )
                    self.assertTrue((workspace / "schema/fixture.json").is_file())
        self.assertEqual(
            (source / "buildSrc/gradle.properties").read_text(),
            "openapiGeneratorVersion=7.11.0\n",
        )

    def run_snapshot_report(
        self, state="Current v72", extra=(), pinned_version=72, worker=None, pr_lookup=None,
    ):
        (self.root / "config").mkdir(exist_ok=True)
        (self.root / "config/services.json").write_text(json.dumps({
            "services": [{"name": "Checkout", "version": 73}]
        }))

        def clone(destination):
            (destination / "config").mkdir(parents=True)
            (destination / "config/services.json").write_text(json.dumps({
                "services": [{"name": "Checkout", "version": pinned_version}]
            }))
            schema = destination / "schema/json"
            schema.mkdir(parents=True)
            (schema / "CheckoutService-v72.json").write_text("{}")
            if worker is not None:
                (schema / "NewService-v1.json").write_text("{}")
            return True

        with (
            mock.patch.object(sdk_coverage, "ROOT", self.root),
            mock.patch.object(sdk_coverage, "PROJECTS", ["java"]),
            mock.patch.object(sdk_coverage, "clone_automation_repo", side_effect=clone),
            mock.patch.object(sdk_coverage, "run_command", return_value=mock.Mock(returncode=0, stdout="abc123")),
            mock.patch.object(
                sdk_coverage, "run_project",
                return_value=("java", {"checkout": state}, {}, False),
                side_effect=worker,
            ) as run_project,
            mock.patch.object(sdk_coverage, "lookup_service_prs", return_value={}, side_effect=pr_lookup),
            mock.patch("sys.argv", ["sdk_coverage.py", *extra]),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            status = sdk_coverage.main()
        return status, run_project

    def test_report_uses_committed_catalog_instead_of_working_tree_edits(self) -> None:
        status, run_project = self.run_snapshot_report()
        self.assertEqual(status, 0)
        self.assertEqual(run_project.call_args.args[3], [{"name": "Checkout", "version": 72}])
        self.assertIn("| Checkout | v72 | Current v72 |", (self.root / "sdk-coverage.md").read_text())

    def test_custom_output_preserves_existing_local_report(self) -> None:
        local_report = self.root / "sdk-coverage.md"
        local_report.write_text("Existing local report")
        output = self.root / "reports/coverage.md"
        status, _ = self.run_snapshot_report(extra=("--output", str(output)))
        self.assertEqual(status, 0)
        self.assertIn("| Checkout | v72 |", output.read_text())
        self.assertEqual(local_report.read_text(), "Existing local report")

    def test_coverage_differences_do_not_fail_the_detailed_report(self) -> None:
        for state in ("Service drift at v72", "Service version behind v71", "Not assessed"):
            with self.subTest(state=state):
                status, _ = self.run_snapshot_report(state=state)
                self.assertEqual(status, 0)

    def test_generation_failure_saves_the_report_and_fails(self) -> None:
        status, _ = self.run_snapshot_report(state="Failed")
        self.assertEqual(status, 1)
        self.assertIn("| Checkout | v72 | Failed |", (self.root / "sdk-coverage.md").read_text())

    def test_confirmed_pr_is_added_without_changing_generation_status(self) -> None:
        pr = sdk_coverage.ServicePullRequest(
            42, "https://github.com/Adyen/adyen-java-api-library/pull/42",
            datetime(2000, 1, 1, tzinfo=timezone.utc),
        )
        status, _ = self.run_snapshot_report(
            state="Behind", pr_lookup=lambda *_: {("java", "checkout"): pr},
        )
        self.assertEqual(status, 0)
        report = (self.root / "sdk-coverage.md").read_text()
        self.assertIn("| Checkout | v72 | Behind · [PR #42]", report)
        self.assertIn("- `Behind`:", report)

    def test_pr_lookup_failure_does_not_fail_or_prevent_report(self) -> None:
        lookup = sdk_coverage.lookup_service_prs
        with mock.patch.object(sdk_coverage, "github_api_json", side_effect=OSError("unavailable")):
            status, _ = self.run_snapshot_report(state="Behind", pr_lookup=lookup)
        self.assertEqual(status, 0)
        report = (self.root / "sdk-coverage.md").read_text()
        self.assertIn("| Checkout | v72 | Behind |", report)
        self.assertNotIn("- PR age:", report)

    def test_missing_spec_saves_the_report_without_failing(self) -> None:
        status, _ = self.run_snapshot_report(pinned_version=73)
        self.assertEqual(status, 0)
        self.assertIn("Catalog entries without an OpenAPI file", (self.root / "sdk-coverage.md").read_text())

    def test_workspace_failure_with_only_missing_specs_saves_report_and_fails(self) -> None:
        with mock.patch.object(sdk_coverage, "prepare_project_workspace", return_value=None):
            status, _ = self.run_snapshot_report(
                pinned_version=73, worker=sdk_coverage.run_project,
            )
        self.assertEqual(status, 1)
        report = (self.root / "sdk-coverage.md").read_text()
        self.assertIn("| Checkout | v73 | Missing spec |", report)
        self.assertIn("| NewService | v1 | Failed |", report)

    def test_formatter_failure_with_only_missing_specs_saves_report_and_fails(self) -> None:
        with (
            mock.patch.object(sdk_coverage, "prepare_project_workspace", return_value=self.root),
            mock.patch.object(sdk_coverage, "prepare_formatter", return_value=False),
        ):
            status, _ = self.run_snapshot_report(
                pinned_version=73, worker=sdk_coverage.run_project,
            )
        self.assertEqual(status, 1)
        self.assertIn("| Checkout | v73 | Missing spec |", (self.root / "sdk-coverage.md").read_text())

    def test_successful_worker_with_only_missing_specs_is_warning_only(self) -> None:
        with (
            mock.patch.object(sdk_coverage, "prepare_project_workspace", return_value=self.root),
            mock.patch.object(sdk_coverage, "prepare_formatter", return_value=True),
        ):
            status, _ = self.run_snapshot_report(
                pinned_version=73, worker=sdk_coverage.run_project,
            )
        self.assertEqual(status, 0)

    def test_invalid_snapshot_catalog_fails_cleanly(self) -> None:
        with mock.patch.object(sdk_coverage, "load_services", side_effect=ValueError("invalid catalog")):
            status, worker = self.run_snapshot_report()
        self.assertEqual(status, 1)
        worker.assert_not_called()

    def test_detailed_report_uses_validated_catalog_loader(self) -> None:
        config = self.root / "config"
        config.mkdir()
        (config / "services.json").write_text(json.dumps({
            "services": [{"name": "Checkout", "version": True}],
        }))
        with self.assertRaises(ValueError):
            sdk_coverage.load_services(self.root)


class TestCheckService(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.workspace = Path(directory.name)
        self.service = {"name": "Checkout", "version": 72}
        self.repo = self.workspace / "java/repo"
        self.repo.mkdir(parents=True)
        schema = self.workspace / "schema/json"
        schema.mkdir(parents=True)
        (schema / "CheckoutService-v72.json").write_text("{}")
        for name, value in (
            ("clean_temporary_sdk", True),
            ("read_service_version", 72),
            ("changed_repo_paths", []),
            ("run_command", mock.Mock(returncode=0, stdout="")),
        ):
            patcher = mock.patch.object(sdk_coverage, name, return_value=value)
            setattr(self, name, patcher.start())
            self.addCleanup(patcher.stop)

    def write_source(self) -> None:
        source = self.repo / "src/main/java/com/adyen/service/checkout/CheckoutApi.java"
        source.parent.mkdir(parents=True)
        source.write_text("class CheckoutApi {}")

    def check(self) -> str:
        with contextlib.redirect_stdout(io.StringIO()):
            return sdk_coverage.check_service(self.workspace, "java", self.service)

    def test_no_output_without_sources_is_not_current(self) -> None:
        self.assertEqual(self.check(), "Not assessed")

    def test_matching_sources_without_changes_are_current(self) -> None:
        self.write_source()
        self.assertEqual(self.check(), "Current v72")

    def test_wrong_existing_version_without_changes_is_not_current(self) -> None:
        self.write_source()
        self.read_service_version.return_value = 71
        self.assertEqual(self.check(), "Not assessed")

    def test_skipped_webhook_deployments_are_unsupported(self) -> None:
        for project in ("python", "ruby"):
            with self.subTest(project=project):
                self.assertEqual(
                    sdk_coverage.check_service(
                        self.workspace, project, {"name": "AcsWebhooks", "version": 1}
                    ),
                    "Unsupported; presence not assessed",
                )
        self.run_command.assert_not_called()

    def test_catalog_excluded_service_is_unsupported_before_spec_lookup(self) -> None:
        service = {"name": "Tapi", "version": 1, "projects": ["node"]}
        self.assertEqual(
            sdk_coverage.check_service(self.workspace, "java", service),
            "Unsupported; presence not assessed",
        )
        self.run_command.assert_not_called()
        self.clean_temporary_sdk.assert_not_called()

    def test_generation_failure_is_still_reported(self) -> None:
        self.run_command.return_value = mock.Mock(returncode=1, stdout="generation failed")
        self.assertEqual(self.check(), "Failed")

    def test_missing_spec_skips_generation_with_a_warning(self) -> None:
        (self.workspace / "schema/json/CheckoutService-v72.json").unlink()
        self.assertEqual(self.check(), "Missing spec")
        self.run_command.assert_not_called()
        self.clean_temporary_sdk.assert_not_called()


class TestUnsupportedPresence(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.repo = Path(directory.name)
        self.commit = "a" * 40
        self.service = {"name": "AcsWebhooks", "spec": "BalancePlatformAcsNotification", "version": 1}
        self.titles = {"BalancePlatformAcsNotification": "ACS webhooks"}

    def detect(self, sources, project="python", titles=None):
        with (
            mock.patch.object(
                sdk_coverage, "read_committed_sdk_sources",
                return_value=(self.commit, sources),
            ),
            contextlib.redirect_stdout(io.StringIO()) as log,
        ):
            results = sdk_coverage.detect_unsupported_services(
                self.repo, project, [self.service], self.titles if titles is None else titles,
            )
        return results["acswebhooks"], log.getvalue()

    def generated(self, version=None):
        return (
            "# ACS webhooks\n# OpenAPI Generator\n"
            + (f"# The version of the OpenAPI document: {version}\n" if version else "")
            + "class AuthenticationNotification:\n    pass\n"
        )

    def test_generated_family_source_records_version_and_proof(self) -> None:
        status, log = self.detect({"Adyen/models/authentication.py": self.generated(1)})
        self.assertEqual(status, "Unsupported; in SDK at v1")
        self.assertIn(self.commit, log)
        self.assertIn("Adyen/models/authentication.py:1: generated API title", log)
        self.assertIn("source versions [1]", log)

    def test_source_with_no_version_is_present_not_current(self) -> None:
        status, _ = self.detect({"Adyen/models/authentication.py": self.generated()})
        self.assertEqual(status, "Unsupported; in SDK")

    def test_conflicting_versions_stay_unknown(self) -> None:
        for sources in (
            {"Adyen/first.py": self.generated(1), "Adyen/second.py": self.generated(2)},
            {"Adyen/first.py": self.generated(1),
             "sdk-generation-log/acswebhooks.json": '{"specVersion": 2}'},
        ):
            with self.subTest(sources=sources):
                self.assertEqual(self.detect(sources)[0], "Unsupported; in SDK")

    def test_committed_generation_log_can_identify_version(self) -> None:
        status, log = self.detect({
            "Adyen/notification.py": self.generated(),
            "sdk-generation-log/acswebhooks.json": '{"specVersion": 1}',
        })
        self.assertEqual(status, "Unsupported; in SDK at v1")
        self.assertIn("sdk-generation-log/acswebhooks.json: specVersion 1", log)

    def test_known_handwritten_declaration_in_service_path(self) -> None:
        for project, path, content in (
            ("python", "Adyen/services/acsWebhooks.py",
             "class AdyenAcsWebhooksApi:\n    pass\n"),
            ("ruby", "lib/adyen/services/acsWebhooks.rb",
             "class AcsWebhooks\n  DEFAULT_VERSION = 1\nend\n"),
        ):
            with self.subTest(project=project):
                expected = "Unsupported; in SDK" + (" at v1" if project == "ruby" else "")
                status, log = self.detect({path: content}, project)
                self.assertEqual(status, expected)
                self.assertIn("known service path and declaration", log)

    def test_generic_helpers_and_prose_are_not_family_evidence(self) -> None:
        status, _ = self.detect({
            "Adyen/util/hmac_validator.py": (
                "class HmacValidator:\n"
                '    """Validates ACS webhooks produced with OpenAPI Generator.\n'
                "    ACS webhooks\n"
                '    """\n'
            ),
            "Adyen/services/webhooks.py": "class WebhookHandler:\n    pass\n",
        })
        self.assertEqual(status, "Unsupported")

    def test_log_without_matching_source_does_not_prove_presence(self) -> None:
        status, _ = self.detect({"sdk-generation-log/acswebhooks.json": '{"specVersion": 1}'})
        self.assertEqual(status, "Unsupported")

    def test_ambiguous_source_or_shared_title_is_not_assessed(self) -> None:
        self.assertEqual(
            self.detect({"Adyen/services/acsWebhooks.py": "class HmacValidator:\n    pass\n"})[0],
            "Unsupported; presence not assessed",
        )
        self.assertEqual(
            self.detect(
                {"Adyen/notification.py": self.generated(1)},
                titles={**self.titles, "OtherNotification": "ACS webhooks"},
            )[0],
            "Unsupported; presence not assessed",
        )

    def test_exact_title_without_generator_header_is_not_evidence(self) -> None:
        status, _ = self.detect({
            "Adyen/example.py": "# ACS webhooks\nclass Example:\n    pass\n",
        })
        self.assertEqual(status, "Unsupported")

    def test_evidence_order_does_not_change_result_or_log(self) -> None:
        sources = {"Adyen/z.py": self.generated(1), "Adyen/a.py": self.generated(1)}
        self.assertEqual(self.detect(sources), self.detect(dict(reversed(list(sources.items())))))

    def test_git_reader_uses_pinned_blobs_not_working_tree(self) -> None:
        source = self.repo / "Adyen/services/acsWebhooks.py"
        source.parent.mkdir(parents=True)
        source.write_text("uncommitted content")
        blob = "b" * 40
        content = self.generated(1).encode()
        tree = (
            f"100644 blob {blob}\tAdyen/services/acsWebhooks.py\0"
            f"100644 blob {'c' * 40}\tAdyen/tests/fake.py\0"
            f"120000 blob {'d' * 40}\tAdyen/linked.py\0"
            f"100644 blob {'e' * 40}\tAdyen/example.rb\0"
        )
        with (
            mock.patch.object(sdk_coverage, "run_command", side_effect=[
                mock.Mock(returncode=0, stdout=self.commit + "\n"),
                mock.Mock(returncode=0, stdout=tree),
            ]) as git,
            mock.patch.object(sdk_coverage.subprocess, "run", return_value=mock.Mock(
                returncode=0,
                stdout=f"{blob} blob {len(content)}\n".encode() + content + b"\n",
            )) as batch,
        ):
            commit, sources = sdk_coverage.read_committed_sdk_sources(self.repo, "python")
        self.assertEqual(commit, self.commit)
        self.assertEqual(sources, {"Adyen/services/acsWebhooks.py": content.decode()})
        self.assertIn(self.commit, git.call_args_list[1].args[0])
        self.assertEqual(batch.call_args.kwargs["input"], (blob + "\n").encode())
        self.assertEqual(source.read_text(), "uncommitted content")

    def test_failed_git_inspection_is_not_treated_as_absence(self) -> None:
        with mock.patch.object(
            sdk_coverage, "run_command", return_value=mock.Mock(returncode=1, stdout=""),
        ):
            with self.assertRaises(OSError):
                sdk_coverage.read_committed_sdk_sources(self.repo, "python")


class TestRunProject(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.workspace = self.root / "workspace"
        self.workspace.mkdir()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_missing_spec_is_not_passed_to_generation(self) -> None:
        schema = self.root / "schema/json"
        schema.mkdir(parents=True)
        (schema / "CheckoutService-v72.json").write_text("{}")
        checkout = {"name": "Checkout", "version": 72}
        payout = {"name": "Payout", "version": 68}
        with (
            mock.patch.object(sdk_coverage, "prepare_project_workspace", return_value=self.workspace),
            mock.patch.object(sdk_coverage, "run_command", return_value=mock.Mock(returncode=0, stdout="")),
            mock.patch.object(sdk_coverage, "prepare_formatter", return_value=True),
            mock.patch.object(sdk_coverage, "check_service", return_value="Current v72") as check_service,
            contextlib.redirect_stdout(io.StringIO()),
        ):
            _, results, _, failed = sdk_coverage.run_project(
                self.root, self.root / "schema", "go", [checkout, payout], [], {},
            )
        self.assertEqual(results, {"checkout": "Current v72", "payout": "Missing spec"})
        self.assertFalse(failed)
        check_service.assert_called_once_with(self.workspace, "go", checkout)

    def test_formatter_failure_returns_consistent_tuple(
            self,
    ) -> None:
        # Regression: the formatter-failure path once
        # returned a differently shaped tuple and crashed
        # main() while unpacking the worker results.
        with mock.patch.object(
                sdk_coverage,
                "prepare_project_workspace",
                return_value=self.workspace,
        ):
            with mock.patch.object(
                    sdk_coverage,
                    "run_command",
                    return_value=mock.Mock(
                        returncode=0,
                        stdout="",
                    ),
            ):
                with mock.patch.object(
                        sdk_coverage,
                        "prepare_formatter",
                        return_value=False,
                ):
                    result = (
                        sdk_coverage
                        .run_project(
                            self.root,
                            self.root / "schema",
                            "go",
                            [],
                            [],
                            {},
                        )
                    )

        self.assertEqual(len(result), 4)
        project, service_results, findings, failed = result

        self.assertEqual(project, "go")
        self.assertEqual(service_results, {})
        self.assertEqual(findings, {})
        self.assertTrue(failed)

    def test_workspace_failure_returns_consistent_tuple(
            self,
    ) -> None:
        with mock.patch.object(
                sdk_coverage,
                "prepare_project_workspace",
                return_value=None,
        ):
            result = sdk_coverage.run_project(
                self.root,
                self.root / "schema",
                "go",
                [],
                [],
                {},
            )

        self.assertEqual(len(result), 4)
        self.assertIsNone(result[2])
        self.assertTrue(result[3])

    def test_clone_failure_returns_consistent_tuple(
            self,
    ) -> None:
        with mock.patch.object(
                sdk_coverage,
                "prepare_project_workspace",
                return_value=self.workspace,
        ):
            with mock.patch.object(
                    sdk_coverage,
                    "run_command",
                    return_value=mock.Mock(
                        returncode=1,
                        stdout="",
                    ),
            ):
                result = sdk_coverage.run_project(
                    self.root,
                    self.root / "schema",
                    "go",
                    [],
                    [],
                    {},
                )

        self.assertEqual(len(result), 4)
        self.assertIsNone(result[2])
        self.assertTrue(result[3])

    def test_unsupported_webhooks_keep_their_status_on_every_worker_path(self) -> None:
        schema = self.root / "schema/json"
        schema.mkdir(parents=True)
        for project in ("python", "ruby"):
            for phase in ("missing", "workspace", "clone", "formatter", "scan"):
                with (
                    self.subTest(project=project, phase=phase),
                    mock.patch.object(
                        sdk_coverage, "prepare_project_workspace",
                        return_value=None if phase == "workspace" else self.workspace,
                    ),
                    mock.patch.object(
                        sdk_coverage, "run_command",
                        return_value=mock.Mock(returncode=1 if phase == "clone" else 0, stdout=""),
                    ),
                    mock.patch.object(
                        sdk_coverage, "detect_sdk_families",
                        return_value={}, side_effect=OSError("scan failed") if phase == "scan" else None,
                    ),
                    mock.patch.object(
                        sdk_coverage, "detect_unsupported_services",
                        return_value={"acswebhooks": "Unsupported"},
                    ),
                    mock.patch.object(sdk_coverage, "prepare_formatter", return_value=phase != "formatter"),
                    mock.patch.object(sdk_coverage, "check_service") as generate,
                    contextlib.redirect_stdout(io.StringIO()),
                ):
                    spec = schema / "AcsWebhooks-v1.json"
                    if phase == "missing":
                        spec.unlink(missing_ok=True)
                    else:
                        spec.write_text("{}")
                    result = sdk_coverage.run_project(
                        self.root, schema.parent, project,
                        [{"name": "AcsWebhooks", "version": 1}], [], {},
                    )
                    expected = (
                        "Unsupported; presence not assessed"
                        if phase in {"workspace", "clone"} else "Unsupported"
                    )
                    self.assertEqual(result[1], {"acswebhooks": expected})
                    self.assertEqual(result[3], phase != "missing")
                    generate.assert_not_called()

    def test_unsupported_presence_survives_formatter_failure(self) -> None:
        with (
            mock.patch.object(sdk_coverage, "prepare_project_workspace", return_value=self.workspace),
            mock.patch.object(sdk_coverage, "run_command", return_value=mock.Mock(returncode=0, stdout="")),
            mock.patch.object(sdk_coverage, "detect_sdk_families", return_value={}),
            mock.patch.object(
                sdk_coverage, "detect_unsupported_services",
                return_value={"acswebhooks": "Unsupported; in SDK at v1"},
            ) as detect,
            mock.patch.object(sdk_coverage, "prepare_formatter", return_value=False),
            mock.patch.object(sdk_coverage, "check_service") as generate,
            contextlib.redirect_stdout(io.StringIO()),
        ):
            result = sdk_coverage.run_project(
                self.root, self.root / "schema", "python",
                [{"name": "AcsWebhooks", "version": 1}], [], {},
            )
        self.assertEqual(result[1], {"acswebhooks": "Unsupported; in SDK at v1"})
        self.assertTrue(result[3])
        detect.assert_called_once()
        generate.assert_not_called()

    def test_presence_inspection_failure_fails_worker_without_claiming_absence(self) -> None:
        with (
            mock.patch.object(sdk_coverage, "prepare_project_workspace", return_value=self.workspace),
            mock.patch.object(sdk_coverage, "run_command", return_value=mock.Mock(returncode=0, stdout="")),
            mock.patch.object(sdk_coverage, "detect_unsupported_services", side_effect=OSError("unreadable")),
            mock.patch.object(sdk_coverage, "prepare_formatter") as formatter,
            contextlib.redirect_stdout(io.StringIO()),
        ):
            result = sdk_coverage.run_project(
                self.root, self.root / "schema", "python",
                [{"name": "AcsWebhooks", "version": 1}], [], {},
            )
        self.assertEqual(result[1], {"acswebhooks": "Unsupported; presence not assessed"})
        self.assertTrue(result[3])
        formatter.assert_not_called()


class TestFormatFamilySdkSummary(unittest.TestCase):
    def test_present_and_absent_projects(self) -> None:
        summary = sdk_coverage.format_family_sdk_summary(
            {
                "java": {
                    "OpenBankingService": (
                        "Present",
                        1,
                    ),
                },
                "node": {
                    "OpenBankingService": (
                        "Absent",
                        None,
                    ),
                },
            },
            "OpenBankingService",
        )

        self.assertEqual(summary, "Java (v1)")

    def test_no_sdk_ships_the_family(self) -> None:
        summary = sdk_coverage.format_family_sdk_summary(
            {
                "java": {
                    "FundService": ("Absent", None),
                },
            },
            "FundService",
        )

        self.assertEqual(summary, "None")

    def test_unassessed_family(self) -> None:
        summary = sdk_coverage.format_family_sdk_summary(
            {
                "java": {
                    "Webhooks": ("Unknown", None),
                },
            },
            "Webhooks",
        )

        self.assertEqual(summary, "Not assessed")


class TestServicePullRequests(unittest.TestCase):
    def make_pr(self, project="java", service_id="checkout", number=42):
        repository = f"Adyen/adyen-{project}-api-library"
        return {
            "number": number,
            "state": "open",
            "merged_at": None,
            "created_at": "2026-10-21T12:00:00Z",
            "updated_at": "2026-11-03T11:59:00Z",
            "base": {"ref": "main", "repo": {"full_name": repository}},
            "head": {"ref": f"sdk-automation/{service_id}", "repo": {"full_name": repository}},
        }

    def test_exact_service_match_uses_creation_time_and_canonical_url(self) -> None:
        pr = self.make_pr()
        pr["html_url"] = "https://example.invalid/not-a-github-pr"
        matches = sdk_coverage.match_service_prs("java", {"checkout"}, "main", [pr])
        self.assertEqual(matches["checkout"], sdk_coverage.ServicePullRequest(
            42, "https://github.com/Adyen/adyen-java-api-library/pull/42",
            datetime(2026, 10, 21, 12, tzinfo=timezone.utc),
        ))

    def test_unconfirmed_matches_are_omitted(self) -> None:
        for path, value in (
            (("state",), "closed"),
            (("merged_at",), "2026-11-02T12:00:00Z"),
            (("base", "ref"), "release"),
            (("base", "repo", "full_name"), "Adyen/adyen-node-api-library"),
            (("head", "repo", "full_name"), "Other/adyen-java-api-library"),
            (("head", "repo"), None),
            (("head", "ref"), "feature/checkout"),
            (("head", "ref"), "sdk-automation/Checkout"),
            (("head", "ref"), "sdk-automation/checkout-extra"),
            (("number",), True),
            (("number",), 0),
            (("created_at",), None),
            (("created_at",), "not a timestamp"),
            (("created_at",), "2026-02-30T12:00:00Z"),
        ):
            with self.subTest(path=path, value=value):
                pr = self.make_pr()
                pr["title"] = "[checkout] Code generation: update services and models"
                target = pr
                for part in path[:-1]:
                    target = target[part]
                target[path[-1]] = value
                self.assertEqual(
                    sdk_coverage.match_service_prs("java", {"checkout"}, "main", [pr]), {},
                )

    def test_ambiguous_service_prs_are_not_guessed(self) -> None:
        self.assertEqual(
            sdk_coverage.match_service_prs(
                "java", {"checkout"}, "main", [self.make_pr(number=42), self.make_pr(number=43)],
            ),
            {},
        )

    def test_drafts_and_case_insensitive_repository_names_are_supported(self) -> None:
        pr = self.make_pr()
        pr["draft"] = True
        pr["head"]["repo"]["full_name"] = pr["head"]["repo"]["full_name"].lower()
        self.assertIn("checkout", sdk_coverage.match_service_prs("java", {"checkout"}, "main", [pr]))

    def test_default_branch_is_not_assumed_to_be_main(self) -> None:
        pr = self.make_pr(project="ruby", service_id="payment")
        pr["base"]["ref"] = "master"
        self.assertIn(
            "payment", sdk_coverage.match_service_prs("ruby", {"payment"}, "master", [pr]),
        )

    def test_only_drift_and_behind_results_trigger_lookup(self) -> None:
        for status, expected in (
            ("Service drift at v72", True),
            ("Service version behind v71", True),
            ("Behind", True),
            ("Current v72", False),
            ("Failed", False),
            ("Missing spec", False),
            ("Unsupported", False),
            ("Unsupported; in SDK at v1", False),
            ("In SDK", False),
            ("Not assessed", False),
        ):
            with self.subTest(status=status):
                self.assertEqual(sdk_coverage.supports_pr_age(status), expected)

    def test_unselected_results_do_not_trigger_network_requests(self) -> None:
        with (
            mock.patch.object(sdk_coverage, "PROJECTS", ["java"]),
            mock.patch.object(sdk_coverage, "github_api_json") as api,
        ):
            self.assertEqual(sdk_coverage.lookup_service_prs(
                [{"name": "Checkout", "version": 72}],
                {("java", "checkout"): "Current v72", ("java", "unselected"): "Behind"},
            ), {})
        api.assert_not_called()

    def test_lookup_paginates_and_matches_only_affected_sdk(self) -> None:
        first_page = [
            self.make_pr(service_id=f"other{index}", number=index + 1)
            for index in range(100)
        ]
        with (
            mock.patch.object(sdk_coverage, "PROJECTS", ["java", "node"]),
            mock.patch.object(
                sdk_coverage, "github_api_json",
                side_effect=[{"default_branch": "main"}, first_page, [self.make_pr()]],
            ) as api,
            contextlib.redirect_stdout(io.StringIO()),
        ):
            matches = sdk_coverage.lookup_service_prs(
                [{"name": "Checkout", "version": 72}],
                {("java", "checkout"): "Behind", ("node", "checkout"): "Current v72"},
            )
        self.assertEqual(set(matches), {("java", "checkout")})
        self.assertEqual(api.call_count, 3)
        self.assertIn("base=main", api.call_args_list[1].args[0])
        self.assertIn("page=2", api.call_args_list[2].args[0])
        self.assertTrue(all("adyen-java-api-library" in call.args[0] for call in api.call_args_list))

    def test_incomplete_listing_does_not_produce_partial_matches(self) -> None:
        first_page = [self.make_pr()] + [
            self.make_pr(service_id=f"other{index}", number=index + 100)
            for index in range(99)
        ]
        with (
            mock.patch.object(sdk_coverage, "PROJECTS", ["java"]),
            mock.patch.object(
                sdk_coverage, "github_api_json",
                side_effect=[{"default_branch": "main"}, first_page, OSError("private details")],
            ),
            contextlib.redirect_stdout(io.StringIO()) as output,
        ):
            matches = sdk_coverage.lookup_service_prs(
                [{"name": "Checkout", "version": 72}], {("java", "checkout"): "Behind"},
            )
        self.assertEqual(matches, {})
        self.assertIn("ages omitted", output.getvalue())
        self.assertNotIn("private details", output.getvalue())

    def test_pagination_limit_omits_ages_without_guessing(self) -> None:
        with (
            mock.patch.object(sdk_coverage, "PROJECTS", ["java"]),
            mock.patch.object(
                sdk_coverage, "github_api_json",
                side_effect=[{"default_branch": "main"}] + [[self.make_pr()] * 100] * 10,
            ) as api,
            contextlib.redirect_stdout(io.StringIO()),
        ):
            matches = sdk_coverage.lookup_service_prs(
                [{"name": "Checkout", "version": 72}], {("java", "checkout"): "Behind"},
            )
        self.assertEqual(matches, {})
        self.assertEqual(api.call_count, 11)

    def test_api_failures_and_invalid_responses_are_warning_only(self) -> None:
        for responses in (
            [HTTPError("https://api.github.com", 403, "Forbidden", {}, None)],
            [TimeoutError("unavailable")],
            [[]],
            [{"default_branch": ""}],
            [{"default_branch": "main"}, {}],
            [{"default_branch": "main"}, [None]],
        ):
            with (
                self.subTest(responses=responses),
                mock.patch.object(sdk_coverage, "PROJECTS", ["java"]),
                mock.patch.object(sdk_coverage, "github_api_json", side_effect=responses),
                contextlib.redirect_stdout(io.StringIO()) as output,
            ):
                self.assertEqual(sdk_coverage.lookup_service_prs(
                    [{"name": "Checkout", "version": 72}], {("java", "checkout"): "Behind"},
                ), {})
                self.assertIn("Warning:", output.getvalue())

    def test_api_authentication_is_optional_and_credentials_are_not_in_urls(self) -> None:
        for environment, token in (
            ({}, None),
            ({"GH_TOKEN": "unit-test-token"}, "unit-test-token"),
            ({"GITHUB_TOKEN": "fallback-test-token"}, "fallback-test-token"),
            ({"GH_TOKEN": "preferred-test-token", "GITHUB_TOKEN": "other"}, "preferred-test-token"),
        ):
            response = io.BytesIO(b'{"default_branch": "main"}')
            with (
                self.subTest(environment=environment),
                mock.patch.dict(os.environ, environment, clear=True),
                mock.patch.object(sdk_coverage, "urlopen", return_value=response) as opener,
            ):
                self.assertEqual(
                    sdk_coverage.github_api_json("/repos/Adyen/adyen-java-api-library"),
                    {"default_branch": "main"},
                )
            request = opener.call_args.args[0]
            self.assertEqual(request.full_url, "https://api.github.com/repos/Adyen/adyen-java-api-library")
            self.assertEqual(request.get_header("Authorization"), f"Bearer {token}" if token else None)
            self.assertEqual(opener.call_args.kwargs["timeout"], 20)
            self.assertTrue(response.closed)


class TestServicePullRequestAge(unittest.TestCase):
    report_time = datetime(2026, 11, 3, 12, tzinfo=timezone.utc)

    def build(self, status="Service drift at v72", created_at=None, report_time=None):
        pr = sdk_coverage.ServicePullRequest(
            42, "https://github.com/Adyen/adyen-java-api-library/pull/42",
            created_at or datetime(2026, 10, 21, 12, tzinfo=timezone.utc),
        )
        with mock.patch.object(sdk_coverage, "PROJECTS", ["java"]):
            return sdk_coverage.build_report(
                [{"name": "Checkout", "version": 72}],
                {("java", "checkout"): status},
                [], [], [], {}, {},
                service_prs={("java", "checkout"): pr},
                report_time=report_time or self.report_time,
            )

    def test_fixed_snapshot_and_timestamp_produce_identical_reports(self) -> None:
        first, second = self.build(), self.build()
        self.assertEqual(first, second)
        self.assertIn("Generated at: `2026-11-03T12:00:00+00:00`", first)
        self.assertIn(
            "Service drift at v72 · [PR #42](https://github.com/Adyen/adyen-java-api-library/pull/42)"
            " · open 13 days",
            first,
        )
        self.assertIn("- `Service drift at vN`:", first)
        self.assertNotIn("- `Current vN`:", first)
        self.assertIn("a pull request (PR) is a proposed SDK update", first)
        self.assertIn("full 24-hour days from its creation to this report's time", first)
        self.assertIn("This is not how long the SDK has been behind", first)
        self.assertIn("may not fix every difference", first)
        self.assertNotIn("sdk-automation/<service-id>", first)

    def test_age_is_completed_24_hour_days(self) -> None:
        for elapsed, expected in (
            (timedelta(hours=23, minutes=59), "open 0 days"),
            (timedelta(days=1), "open 1 day"),
            (timedelta(days=1, hours=23, minutes=59), "open 1 day"),
            (timedelta(days=2), "open 2 days"),
        ):
            with self.subTest(elapsed=elapsed):
                report = self.build(created_at=self.report_time - elapsed)
                self.assertIn(f" · {expected} |", report)

    def test_report_timestamp_is_normalized_to_utc(self) -> None:
        local = self.report_time.astimezone(timezone(timedelta(hours=5, minutes=30)))
        self.assertEqual(self.build(report_time=local), self.build())

    def test_future_creation_times_are_not_reported_as_zero(self) -> None:
        report = self.build(created_at=self.report_time + timedelta(seconds=1))
        self.assertNotIn("[PR #", report)
        self.assertNotIn("- PR age:", report)
        self.assertIn("| Checkout | v72 | Service drift at v72 |", report)

    def test_naive_report_timestamp_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "timezone"):
            self.build(report_time=datetime(2026, 11, 3, 12))

    def test_only_eligible_statuses_receive_annotations(self) -> None:
        for status, expected in (
            ("Service drift at v72", True),
            ("Service version behind v71", True),
            ("Behind", True),
            ("Current v72", False),
            ("Failed", False),
            ("Missing spec", False),
            ("Unsupported", False),
            ("Not assessed", False),
        ):
            with self.subTest(status=status):
                report = self.build(status)
                self.assertEqual("[PR #42]" in report, expected)
                self.assertEqual("- PR age:" in report, expected)


class TestBuildReport(unittest.TestCase):
    def build_for_statuses(self, statuses, project="java"):
        services = [
            {"name": f"Example{index}", "version": 72}
            for index in range(len(statuses))
        ]
        results = {
            (project, service["name"].lower()): status
            for service, status in zip(services, statuses)
        }
        with mock.patch.object(sdk_coverage, "PROJECTS", [project]):
            return sdk_coverage.build_report(services, results, [], [], [], {}, {})

    def test_unsupported_presence_labels_are_rendered_without_generation_claims(self) -> None:
        with mock.patch.object(sdk_coverage, "PROJECTS", ["python", "ruby"]):
            report = sdk_coverage.build_report(
                [{"name": "AcsWebhooks", "version": 1}],
                {("python", "acswebhooks"): "Unsupported; in SDK at v1",
                 ("ruby", "acswebhooks"): "Unsupported"},
                [], [], [], {}, {},
            )
        self.assertIn(
            "| AcsWebhooks | v1 | Unsupported; in SDK at v1 | Unsupported |", report,
        )
        self.assertNotIn("not detected", report)
        self.assertIn("This does not confirm that every feature is supported.", report)

    def test_header_omits_openapi_commit(self) -> None:
        report = sdk_coverage.build_report([], {}, [], [], [], {}, {})
        self.assertIn("# SDK coverage", report)
        self.assertIn("Generated at:", report)
        self.assertNotIn("OpenAPI commit:", report)
        self.assertNotIn("Notes:", report)

    def test_status_descriptions_explain_limits(self) -> None:
        statuses = (
            "Current v72", "Service version behind v71", "Service drift at v72",
            "Behind", "Failed", "Missing spec", "Unsupported",
            "Unsupported; in SDK at v3", "Unsupported; in SDK",
            "Unsupported; presence not assessed",
        )
        services = [
            {"name": f"Example{index}", "version": 72}
            for index in range(len(statuses))
        ]
        findings = {
            "VersionedService": ("Present", 1),
            "UnversionedService": ("Present", None),
            "AbsentService": ("Absent", None),
            "UnknownService": ("Unknown", None),
        }
        with mock.patch.object(sdk_coverage, "PROJECTS", ["java"]):
            report = sdk_coverage.build_report(
                services,
                {("java", service["name"].lower()): status
                 for service, status in zip(services, statuses)},
                [(family, 1) for family in findings], [], [],
                {"java": findings}, {},
            )
        notes = report.split("Notes:\n\n", 1)[1]
        labels = (
            "`Current vN`",
            "`Service version behind vX`",
            "`Service drift at vN`",
            "`Behind`",
            "`Failed`",
            "`Missing spec`",
            "`Unsupported`",
            "`Unsupported; in SDK at vN`",
            "`Unsupported; in SDK`",
            "`Unsupported; presence not assessed`",
            "Services missing from the automation list",
            "`In SDK at vN`",
            "`In SDK`",
            "`Not catalogued`",
            "`Not assessed`",
        )
        for label in labels:
            with self.subTest(label=label):
                self.assertIn(f"- {label}: ", notes)
        for explanation in (
            "may not be the latest available",
            "changes to the tools that build the SDK",
            "A manual review is needed",
            "does not mean the SDK is out of date",
            "Some SDKs may already include them",
            "does not mean it is missing or unsupported",
        ):
            with self.subTest(explanation=explanation):
                self.assertIn(explanation, notes)
        self.assertIn("an SDK is the library an application uses to connect to Adyen", notes)
        for technical_term in (
            "generation catalog", "family-specific", "matching declaration",
            "sdk-automation/<service-id>", "hashes", "dictionaries",
        ):
            with self.subTest(technical_term=technical_term):
                self.assertNotIn(technical_term, notes)

    def test_each_catalogued_status_only_adds_its_own_explanation(self) -> None:
        cases = {
            "Current v72": "Current vN",
            "Service version behind v71": "Service version behind vX",
            "Service drift at v72": "Service drift at vN",
            "Behind": "Behind",
            "Failed": "Failed",
            "Missing spec": "Missing spec",
            "Unsupported": "Unsupported",
            "Unsupported; in SDK at v3": "Unsupported; in SDK at vN",
            "Unsupported; in SDK": "Unsupported; in SDK",
            "Unsupported; presence not assessed": "Unsupported; presence not assessed",
            "Not assessed": "Not assessed",
        }
        for status, expected in cases.items():
            with self.subTest(status=status):
                notes = self.build_for_statuses([status]).split("Notes:\n\n", 1)[1]
                labels = {
                    line.split("`")[1] for line in notes.splitlines()
                    if line.startswith("- `")
                }
                self.assertEqual(labels, {expected})

    def test_repeated_statuses_have_one_explanation(self) -> None:
        report = self.build_for_statuses(["Current v72", "Current v72"])
        self.assertEqual(report.count("- `Current vN`: "), 1)

    def test_unused_results_do_not_add_notes(self) -> None:
        with mock.patch.object(sdk_coverage, "PROJECTS", ["java"]):
            report = sdk_coverage.build_report(
                [{"name": "Checkout", "version": 72}],
                {
                    ("java", "checkout"): "Current v72",
                    ("ruby", "checkout"): "Failed",
                    ("java", "unselected"): "Behind",
                },
                [], [], [], {}, {},
            )
        self.assertIn("- `Current vN`: ", report)
        self.assertNotIn("- `Failed`: ", report)
        self.assertNotIn("- `Behind`: ", report)
        self.assertNotIn("- Ruby:", report)

    def test_catalogued_only_report_omits_unrelated_context(self) -> None:
        report = self.build_for_statuses(["Current v72"])
        for note in (
            "Baseline reason:", "Empty baseline reason cells:", "`No baseline entry`:",
            "Services missing from the automation list:", "- Search limits:",
            "- Code checks:", "- What 'in SDK' means:",
            "- Python:", "- Ruby:",
        ):
            with self.subTest(note=note):
                self.assertNotIn(note, report)

    def test_unsupported_only_report_omits_presence_and_language_notes(self) -> None:
        for project in ("python", "ruby"):
            with self.subTest(project=project):
                report = self.build_for_statuses(["Unsupported"], project)
                self.assertNotIn("- Code checks:", report)
                self.assertNotIn("- What 'in SDK' means:", report)
                self.assertNotIn("- Python:", report)
                self.assertNotIn("- Ruby:", report)

    def test_language_notes_require_generated_service_results(self) -> None:
        for project in ("python", "ruby"):
            for status in (
                "Current v72", "Service drift at v72", "Service version behind v71",
                "Behind", "Failed", "Missing spec", "Not assessed", "Unsupported",
            ):
                with self.subTest(project=project, status=status):
                    report = self.build_for_statuses([status], project)
                    expected = status not in {"Failed", "Missing spec", "Not assessed", "Unsupported"}
                    note = f"- {sdk_coverage.PROJECT_LABELS[project]}:"
                    self.assertEqual(note in report, expected)
                    if expected:
                        self.assertIn(
                            f"{note} only service code is compared. This SDK does "
                            "not have separate generated data models to compare.",
                            report,
                        )

    def test_python_and_ruby_share_one_plain_language_note(self) -> None:
        with mock.patch.object(sdk_coverage, "PROJECTS", ["python", "ruby"]):
            report = sdk_coverage.build_report(
                [{"name": "Checkout", "version": 72}],
                {("python", "checkout"): "Current v72", ("ruby", "checkout"): "Current v72"},
                [], [], [], {}, {},
            )
        self.assertEqual(report.count("- Python and Ruby:"), 1)
        self.assertNotIn("- Python:", report)
        self.assertNotIn("- Ruby:", report)
        self.assertIn(
            "- Python and Ruby: only service code is compared. These SDKs do "
            "not have separate generated data models to compare.",
            report,
        )

    def test_non_webhook_presence_omits_webhook_and_language_notes(self) -> None:
        report = self.build_for_statuses(["Unsupported; in SDK at v3"], "go")
        self.assertIn("- Code checks:", report)
        self.assertIn("`sdk-coverage.log`", report)
        self.assertIn("This does not confirm that every feature is supported.", report)
        self.assertNotIn("webhook", report.lower())
        self.assertNotIn("HMAC", report)
        self.assertNotIn("- Python:", report)
        self.assertNotIn("- Ruby:", report)

    def test_uncatalogued_notes_follow_displayed_findings(self) -> None:
        for state, version, label in (
            ("Present", 1, "In SDK at vN"),
            ("Present", None, "In SDK"),
            ("Absent", None, "Not catalogued"),
            ("Unknown", None, "Not assessed"),
            (None, None, "Failed"),
        ):
            with self.subTest(state=state, version=version):
                findings = (
                    {"java": {"ExampleService": (state, version)}}
                    if state is not None else {}
                )
                with mock.patch.object(sdk_coverage, "PROJECTS", ["java"]):
                    report = sdk_coverage.build_report(
                        [], {}, [("ExampleService", 1)], [], [], findings, {},
                    )
                notes = report.split("Notes:\n\n", 1)[1]
                labels = {
                    line.split("`")[1] for line in notes.splitlines()
                    if line.startswith("- `")
                }
                self.assertEqual(labels, {label, "No baseline entry"})
                self.assertIn(
                    "- Services missing from the automation list: Adyen publishes "
                    "these APIs, but this automation is not configured to generate "
                    "or update them. Some SDKs may already include them.",
                    notes,
                )
                self.assertEqual("- Search limits:" in notes, state is not None)
                self.assertEqual("- What 'in SDK' means:" in notes, state == "Present")
                self.assertNotIn("- About this check:", notes)

    def test_uncatalogued_labels(self) -> None:
        report = sdk_coverage.build_report(
            [],
            {},
            [
                ("OpenBankingService", 1),
                ("Webhooks", 1),
            ],
            [],
            [],
            {
                "java": {
                    "OpenBankingService": (
                        "Present",
                        1,
                    ),
                    "Webhooks": ("Unknown", None),
                },
                "node": {
                    "OpenBankingService": (
                        "Absent",
                        None,
                    ),
                    "Webhooks": ("Unknown", None),
                },
            },
            {},
        )

        self.assertIn(
            "| OpenBankingService | v1"
            " | In SDK at v1 | Not catalogued"
            " | Failed | Failed | Failed"
            " | Failed | Failed |",
            report,
        )
        self.assertIn(
            "| Webhooks | v1"
            " | Not assessed | Not assessed"
            " | Failed | Failed | Failed"
            " | Failed | Failed |",
            report,
        )
        self.assertIn(
            "- `Not catalogued`: the service is not on the automatic update "
            "list, and this check found no matching code in the SDK. "
            "This does not prove the service is absent.",
            report,
        )
        self.assertIn(
            "| OpenBankingService | 1"
            " | Java (v1) |",
            report,
        )
        self.assertIn(
            "| Webhooks | 1 | Not assessed |",
            report,
        )
        self.assertIn(
            "- `In SDK at vN`: matching service code was found",
            report,
        )


class TestBaselineReasons(unittest.TestCase):
    def build(self, baseline):
        return sdk_coverage.build_report(
            [], {},
            [("FundService", 6), ("CloudDeviceService", 1), ("NewService", 1)],
            [({"name": "BalanceControl", "version": 1}, 2),
             ({"name": "Checkout", "version": 71}, 72)],
            [],
            {"java": {
                "FundService": ("Present", 6),
                "CloudDeviceService": ("Present", None),
                "NewService": ("Absent", None),
            }},
            {},
            baseline,
        )

    def test_reasons_are_copied_or_labelled(self) -> None:
        report = self.build({
            "uncoveredSpecs": {
                "FundService": {"reason": "Classic | legacy API.\n Not generated."},
                "CloudDeviceService": {"reason": "UNREVIEWED: decide later"},
            },
            "pinnedVersions": {
                "BalanceControlService": {"acknowledgedVersion": 2, "reason": "Breaking change."},
                "CheckoutService": {"acknowledgedVersion": 71, "reason": "Old pin."},
            },
        })
        self.assertIn("| FundService | 6 | Java (v6) | Classic \\| legacy API. Not generated. |", report)
        self.assertIn("| CloudDeviceService | 1 | Java |  |", report)
        self.assertIn("| NewService | 1 | None | No baseline entry |", report)
        self.assertIn("| BalanceControl | BalanceControlService | 1 | 2 | Breaking change. |", report)
        self.assertIn("| Checkout | CheckoutService | 71 | 72 | No baseline entry |", report)
        self.assertNotIn("decide later", report)
        self.assertNotIn("Old pin.", report)
        self.assertNotIn("No reviewed reason recorded", report)

    def test_unreviewed_version_pin_renders_an_empty_reason(self) -> None:
        report = self.build({
            "uncoveredSpecs": {},
            "pinnedVersions": {
                "BalanceControlService": {
                    "acknowledgedVersion": 2, "reason": " UNREVIEWED: decide later",
                },
            },
        })
        self.assertIn("| BalanceControl | BalanceControlService | 1 | 2 |  |", report)
        self.assertNotIn("decide later", report)

    def test_empty_or_unreviewed_reasons_are_blank(self) -> None:
        for reason in ("", "  ", "unreviewed: pending"):
            with self.subTest(reason=reason):
                self.assertEqual(sdk_coverage.baseline_reason({"reason": reason}), "")

    def test_missing_baseline_labels_every_row(self) -> None:
        report = self.build(None)
        self.assertIn("| FundService | 6 | Java (v6) | No baseline entry |", report)

    def test_notes_explain_baseline_labels(self) -> None:
        notes = self.build(None).split("Notes:\n\n", 1)[1]
        for label in ("Baseline reason", "`No baseline entry`"):
            with self.subTest(label=label):
                self.assertIn(f"- {label}: ", notes)
        self.assertNotIn("- Empty baseline reason cells:", notes)

    def test_empty_reason_note_only_appears_for_displayed_empty_cells(self) -> None:
        report = self.build({
            "uncoveredSpecs": {"FundService": {"reason": "UNREVIEWED: pending"}},
            "pinnedVersions": {},
        })
        self.assertIn("- Empty baseline reason cells:", report)

    def test_reviewed_reasons_do_not_add_empty_or_missing_entry_notes(self) -> None:
        report = self.build({
            "uncoveredSpecs": {
                "FundService": {"reason": "Reviewed."},
                "CloudDeviceService": {"reason": "Reviewed."},
                "NewService": {"reason": "Reviewed."},
                "NotDisplayedService": {"reason": "UNREVIEWED: pending"},
            },
            "pinnedVersions": {
                "BalanceControlService": {"acknowledgedVersion": 2, "reason": "Reviewed."},
                "CheckoutService": {"acknowledgedVersion": 72, "reason": "Reviewed."},
            },
        })
        self.assertIn("- Baseline reason:", report)
        self.assertNotIn("- Empty baseline reason cells:", report)
        self.assertNotIn("- `No baseline entry`:", report)

if __name__ == "__main__":
    unittest.main()
