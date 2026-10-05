#!/usr/bin/env python3

import re
import unittest
from pathlib import Path


WORKFLOW = Path(__file__).parents[1] / "workflows" / "gradle.yml"


class TestReviewerWorkflow(unittest.TestCase):
    def setUp(self) -> None:
        self.steps = {
            block.splitlines()[0].removeprefix("      - name: "): block
            for block in re.split(r"(?=^      - name: )", WORKFLOW.read_text(), flags=re.M)
            if block.startswith("      - name: ")
        }

    def test_create_or_update_does_not_request_reviewers(self) -> None:
        step = self.steps["Create Pull Request"]

        self.assertIn("        id: pull_request\n", step)
        self.assertNotRegex(step, r"(?m)^\s+reviewers:")

    def test_review_request_only_runs_for_new_pull_requests(self) -> None:
        step = self.steps["Request reviewer for new pull request"]

        self.assertIn(
            "        if: steps.pull_request.outputs.pull-request-operation == 'created'\n",
            step,
        )
        self.assertIn(
            "          PR_NUMBER: ${{ steps.pull_request.outputs.pull-request-number }}\n",
            step,
        )
        self.assertIn(
            "          REVIEWER: ${{ steps.reviewer.outputs.reviewer }}\n", step
        )
        self.assertIn(
            'gh api --method POST "repos/$REPOSITORY/pulls/$PR_NUMBER/requested_reviewers"',
            step,
        )
        self.assertIn('-f "reviewers[]=$REVIEWER"', step)


if __name__ == "__main__":
    unittest.main(verbosity=2)
