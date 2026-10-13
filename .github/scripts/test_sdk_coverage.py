#!/usr/bin/env python3

import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
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


class TestRunProject(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.workspace = self.root / "workspace"
        self.workspace.mkdir()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

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

        self.assertEqual(len(result), 3)
        project, service_results, findings = result

        self.assertEqual(project, "go")
        self.assertEqual(service_results, {})
        self.assertEqual(findings, {})

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

        self.assertEqual(len(result), 3)
        self.assertIsNone(result[2])

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

        self.assertEqual(len(result), 3)
        self.assertIsNone(result[2])


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


class TestBuildReport(unittest.TestCase):
    def test_uncatalogued_labels(self) -> None:
        report = sdk_coverage.build_report(
            [],
            {},
            "abc123",
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
            "- `Not catalogued`: present in OpenAPI but absent",
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
            "- `In SDK at vN`: the SDK already ships",
            report,
        )


if __name__ == "__main__":
    unittest.main()
