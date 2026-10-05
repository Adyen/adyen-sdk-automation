#!/usr/bin/env python3

import os
import re
import subprocess
import tempfile
import textwrap
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

    def test_review_request_retries_once_only_on_failure(self) -> None:
        step = self.steps["Request reviewer for new pull request"]
        script = textwrap.dedent(step.split("        run: |\n", 1)[1])
        mock_commands = """
gh() {
  printf '%s\\n' "$*" >> "$CALL_LOG"
  [ "$(wc -l < "$CALL_LOG")" -gt "$FAILURES" ]
}
sleep() { :; }
"""
        for failures, expected_calls, expected_status in [(0, 1, 0), (1, 2, 0), (2, 2, 1)]:
            with self.subTest(failures=failures), tempfile.TemporaryDirectory() as directory:
                call_log = Path(directory) / "calls"
                result = subprocess.run(
                    ["bash", "--noprofile", "--norc", "-eo", "pipefail", "-c", mock_commands + script],
                    env={
                        **os.environ,
                        "CALL_LOG": str(call_log),
                        "FAILURES": str(failures),
                        "REPOSITORY": "Adyen/adyen-java-api-library",
                        "PR_NUMBER": "123",
                        "REVIEWER": "alice",
                    },
                    capture_output=True,
                    text=True,
                )

                self.assertEqual(result.returncode, expected_status, result.stderr)
                self.assertEqual(
                    call_log.read_text().splitlines(),
                    [
                        "api --method POST repos/Adyen/adyen-java-api-library/pulls/123/"
                        "requested_reviewers -f reviewers[]=alice"
                    ] * expected_calls,
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
