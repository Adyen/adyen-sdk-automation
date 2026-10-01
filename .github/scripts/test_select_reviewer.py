#!/usr/bin/env python3

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import select_reviewer


class TestSelectReviewer(unittest.TestCase):
    def test_parses_comma_separated_reviewers(self) -> None:
        self.assertEqual(
            select_reviewer.parse_reviewers("alice, bob-smith ,carol"),
            ["alice", "bob-smith", "carol"],
        )

    def test_rejects_empty_pool(self) -> None:
        with self.assertRaisesRegex(ValueError, "at least one"):
            select_reviewer.parse_reviewers(" , ")

    def test_rejects_invalid_username(self) -> None:
        with self.assertRaisesRegex(ValueError, "Invalid GitHub username"):
            select_reviewer.parse_reviewers("alice,bob_smith")

        with self.assertRaisesRegex(ValueError, "Invalid GitHub username"):
            select_reviewer.parse_reviewers("alice,bob--smith")

    def test_rejects_duplicate_username(self) -> None:
        with self.assertRaisesRegex(ValueError, "Duplicate GitHub username"):
            select_reviewer.parse_reviewers("alice,bob,Alice")

    def test_rejects_invalid_commit_sha(self) -> None:
        with self.assertRaisesRegex(ValueError, "40-character hexadecimal"):
            select_reviewer.select_reviewer("alice,bob", "not-a-sha")

    def test_selects_reviewer_using_commit_hash_modulo_pool_size(self) -> None:
        reviewers = "alice,bob,carol"

        self.assertEqual(select_reviewer.select_reviewer(reviewers, "0" * 40), "alice")
        self.assertEqual(select_reviewer.select_reviewer(reviewers, ("0" * 39) + "1"), "bob")
        self.assertEqual(select_reviewer.select_reviewer(reviewers, ("0" * 39) + "2"), "carol")
        self.assertEqual(select_reviewer.select_reviewer(reviewers, ("0" * 39) + "3"), "alice")

    def test_same_commit_always_selects_same_reviewer(self) -> None:
        commit_sha = "0123456789abcdef0123456789abcdef01234567"

        first = select_reviewer.select_reviewer("alice,bob,carol", commit_sha)
        second = select_reviewer.select_reviewer("alice,bob,carol", commit_sha)

        self.assertEqual(first, second)

    def test_cli_appends_reviewer_to_github_output(self) -> None:
        with tempfile.NamedTemporaryFile() as output:
            subprocess.run(
                [
                    sys.executable,
                    select_reviewer.__file__,
                    "alice,bob",
                    ("0" * 39) + "1",
                    output.name,
                ],
                check=True,
            )
            result = Path(output.name).read_text()

        self.assertEqual(result, "reviewer=bob\n")


if __name__ == "__main__":
    unittest.main(verbosity=2)
