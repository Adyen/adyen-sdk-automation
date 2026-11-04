#!/usr/bin/env python3

import json
import tempfile
import unittest
from pathlib import Path

import update_readme


API_TABLES = {
    "java": (
        "| API | Description | Service Name | Supported version |\n"
        "|---|---|---|---|\n"
        "| [Checkout API](https://docs.adyen.com/api-explorer/Checkout/71/overview) | Existing description | Checkout | **v71** |\n"
        "| [Payout API](https://docs.adyen.com/api-explorer/Payout/68/overview) | Keep exactly | Payout | **v68** |\n"
    ),
    "dotnet": (
        "| API | Description | Service Name | Supported version |\n"
        "|---|---|---|---|\n"
        "| [Checkout API](https://docs.adyen.com/api-explorer/Checkout/71/overview) | Existing description | [Checkout](Adyen/Checkout) | **v71** |\n"
        "| [Payout API](https://docs.adyen.com/api-explorer/Payout/68/overview) | Keep exactly | [Payout](Adyen/Payout) | **v68** |\n"
    ),
    "go": (
        "| API | Description | Service constructor | Supported version |\n"
        "|---|---|---|---|\n"
        "| [Checkout API](https://docs.adyen.com/api-explorer/Checkout/71/overview) | Existing description | client.Checkout() | **v71** |\n"
        "| [Payout API](https://docs.adyen.com/api-explorer/Payout/68/overview) | Keep exactly | client.Payout() | **v68** |\n"
    ),
    "node": (
        "| API name | API version | Description | API object |\n"
        "|---|---|---|---|\n"
        "| [Checkout API](https://docs.adyen.com/api-explorer/Checkout/71/overview) | v71 | Existing description | [Checkout](/src/services/checkout/index.ts) |\n"
        "| [Payout API](https://docs.adyen.com/api-explorer/Payout/68/overview) | v68 | Keep exactly | [Payout](/src/services/payout/index.ts) |\n"
    ),
    "php": (
        "| API | Description | Service Name | Supported version |\n"
        "|---|---|---|---|\n"
        "| [Checkout API](https://docs.adyen.com/api-explorer/Checkout/71/overview) | Existing description | [Checkout](src/Adyen/Service/Checkout) | **v71** |\n"
        "| [Payout API](https://docs.adyen.com/api-explorer/Payout/68/overview) | Keep exactly | [Payout](src/Adyen/Service/Payout) | **v68** |\n"
    ),
    "python": (
        "| API | Description | Service Name | Supported version |\n"
        "|---|---|---|---|\n"
        "| [Checkout API](https://docs.adyen.com/api-explorer/Checkout/71/overview) | Existing description | checkout | **v71** |\n"
        "| [Payout API](https://docs.adyen.com/api-explorer/Payout/68/overview) | Keep exactly | payouts | **v68** |\n"
    ),
    "ruby": (
        "| API name | API version | Description | API object |\n"
        "|---|---|---|---|\n"
        "| [Checkout API](https://docs.adyen.com/api-explorer/Checkout/71/overview) | v71 | Existing description | [Checkout](lib/adyen/services/checkout.rb) |\n"
        "| [Payout API](https://docs.adyen.com/api-explorer/Payout/68/overview) | v68 | Keep exactly | [Payout](lib/adyen/services/payout.rb) |\n"
    ),
}

WEBHOOK_TABLE = (
    "| Webhooks | Description | Model Name | Supported Version |\n"
    "|---|---|---|---|\n"
    "| [Authentication Webhooks](https://docs.adyen.com/api-explorer/acs-webhook/1/overview) | Existing description | Models | **v1** |\n"
    "| [Report Webhooks](https://docs.adyen.com/api-explorer/report-webhooks/1/overview) | Keep exactly | Reports | **v1** |\n"
)


class TestUpdateReadme(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp_dir.name)
        self.spec = self.directory / "spec.json"
        self.spec.write_text(
            json.dumps(
                {
                    "info": {
                        "title": "Adyen Example API",
                        "description": "First paragraph.\n\nAdditional documentation.",
                    }
                }
            )
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def metadata(
        self,
        project: str,
        service: str = "Checkout",
        version: int = 72,
        docs_path: str = "Checkout",
        webhook: bool = False,
        small: bool = False,
    ) -> update_readme.ServiceMetadata:
        return update_readme.ServiceMetadata(
            project=project,
            service=service,
            version=version,
            docs_path=docs_path,
            spec=self.spec,
            small=small,
            webhook=webhook,
        )

    def write_readme(self, body: str, webhook: bool = False) -> Path:
        readme = self.directory / "README.md"
        heading = "## Supported Webhook versions" if webhook else "## Supported API versions"
        readme.write_text(f"# SDK\n\n{heading}\n\n{body}\nAfter table\n")
        return readme

    def test_updates_only_target_api_row_in_every_project(self) -> None:
        for project, table in API_TABLES.items():
            with self.subTest(project=project):
                readme = self.write_readme(table)
                before = readme.read_text()

                changed = update_readme.update_readme(readme, self.metadata(project))

                self.assertTrue(changed)
                after = readme.read_text()
                self.assertIn("/Checkout/72/overview", after)
                self.assertIn("v72", after)
                before_payout = next(line for line in before.splitlines() if "/Payout/" in line)
                after_payout = next(line for line in after.splitlines() if "/Payout/" in line)
                self.assertEqual(before_payout, after_payout)

    def test_adds_new_api_row_in_every_project(self) -> None:
        for project, table in API_TABLES.items():
            with self.subTest(project=project):
                readme = self.write_readme(table)
                metadata = self.metadata(
                    project,
                    service="Example",
                    version=2,
                    docs_path="example",
                    small=True,
                )

                changed = update_readme.update_readme(readme, metadata)

                self.assertTrue(changed)
                result = readme.read_text()
                self.assertIn("[Example API](https://docs.adyen.com/api-explorer/example/2/overview)", result)
                self.assertIn("First paragraph.", result)
                self.assertIn("v2", result)

    def test_updates_webhook_row_for_publishing_projects(self) -> None:
        for project in ("java", "dotnet", "go", "node", "php"):
            with self.subTest(project=project):
                readme = self.write_readme(WEBHOOK_TABLE, webhook=True)
                metadata = self.metadata(
                    project,
                    service="AcsWebhooks",
                    version=2,
                    docs_path="acs-webhook",
                    webhook=True,
                )

                changed = update_readme.update_readme(readme, metadata)

                self.assertTrue(changed)
                self.assertIn("/acs-webhook/2/overview", readme.read_text())
                self.assertIn("**v2**", readme.read_text())

    def test_adds_new_webhook_row_for_publishing_projects(self) -> None:
        for project in ("java", "dotnet", "go", "node", "php"):
            with self.subTest(project=project):
                readme = self.write_readme(WEBHOOK_TABLE, webhook=True)
                metadata = self.metadata(
                    project,
                    service="ExampleWebhooks",
                    version=2,
                    docs_path="example-webhooks",
                    webhook=True,
                )

                changed = update_readme.update_readme(readme, metadata)

                self.assertTrue(changed)
                result = readme.read_text()
                self.assertIn("/example-webhooks/2/overview", result)
                self.assertIn("**v2**", result)

    def test_skips_webhook_when_project_has_no_webhook_table(self) -> None:
        readme = self.write_readme(API_TABLES["python"])
        before = readme.read_text()

        changed = update_readme.update_readme(
            readme,
            self.metadata(
                "python",
                service="AcsWebhooks",
                docs_path="acs-webhook",
                webhook=True,
            ),
        )

        self.assertFalse(changed)
        self.assertEqual(before, readme.read_text())

    def test_preserves_external_documentation_url(self) -> None:
        url = "https://docs.adyen.com/development-resources/data-protection-api"
        table = (
            "| API | Description | Service Name | Supported version |\n"
            "|---|---|---|---|\n"
            f"| [Data Protection API]({url}) | Existing | dataProtection | **v1** |\n"
        )
        readme = self.write_readme(table)

        update_readme.update_readme(
            readme,
            self.metadata(
                "python",
                service="DataProtection",
                version=2,
                docs_path=url,
                small=True,
            ),
        )

        result = readme.read_text()
        self.assertIn(f"]({url})", result)
        self.assertIn("**v2**", result)

    def test_matches_existing_row_by_service_reference(self) -> None:
        table = (
            "| Webhooks | Description | Model Name | Supported Version |\n"
            "|---|---|---|---|\n"
            "| [Authentication Webhooks](https://docs.adyen.com/api-explorer/Checkout/latest/overview) | Existing | [AcsWebhooks](Adyen/AcsWebhooks/Models) | **v1** |\n"
        )
        readme = self.write_readme(table, webhook=True)

        changed = update_readme.update_readme(
            readme,
            self.metadata(
                "dotnet",
                service="AcsWebhooks",
                version=2,
                docs_path="acs-webhook",
                webhook=True,
            ),
        )

        self.assertTrue(changed)
        result = readme.read_text()
        self.assertIn("/acs-webhook/2/overview", result)
        self.assertEqual(sum("Adyen/AcsWebhooks/Models" in line for line in result.splitlines()), 1)

    def test_fails_on_duplicate_documentation_rows(self) -> None:
        duplicate = API_TABLES["java"].replace(
            "| [Payout API]",
            "| [Checkout duplicate](https://docs.adyen.com/api-explorer/Checkout/70/overview) | Duplicate | Duplicate | **v70** |\n"
            "| [Payout API]",
        )
        readme = self.write_readme(duplicate)

        with self.assertRaisesRegex(ValueError, "contains 2 rows"):
            update_readme.update_readme(readme, self.metadata("java"))

    def test_uses_spec_title_to_disambiguate_duplicate_documentation_paths(self) -> None:
        duplicate = API_TABLES["java"].replace("[Checkout API]", "[Example API]").replace(
            "| [Payout API]",
            "| [Legacy Checkout](https://docs.adyen.com/api-explorer/Checkout/70/overview) | Duplicate | Duplicate | **v70** |\n"
            "| [Payout API]",
        )
        readme = self.write_readme(duplicate)

        changed = update_readme.update_readme(readme, self.metadata("java"))

        self.assertTrue(changed)
        result = readme.read_text()
        self.assertIn("[Example API](https://docs.adyen.com/api-explorer/Checkout/72/overview)", result)
        self.assertIn("[Legacy Checkout](https://docs.adyen.com/api-explorer/Checkout/70/overview)", result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
