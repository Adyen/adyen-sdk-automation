#!/usr/bin/env python3

"""Select a deterministic reviewer for an OpenAPI commit."""

import argparse
import re
from pathlib import Path

GITHUB_USERNAME = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$")
COMMIT_SHA = re.compile(r"^[0-9a-fA-F]{40}$")


def parse_reviewers(value: str) -> list[str]:
    reviewers = [reviewer.strip() for reviewer in value.split(",") if reviewer.strip()]
    if not reviewers:
        raise ValueError("SDK_REVIEWERS must contain at least one GitHub username")

    invalid = [
        reviewer
        for reviewer in reviewers
        if not GITHUB_USERNAME.fullmatch(reviewer) or "--" in reviewer
    ]
    if invalid:
        raise ValueError(f"Invalid GitHub username(s): {', '.join(invalid)}")

    normalized_reviewers = [reviewer.casefold() for reviewer in reviewers]
    duplicates = sorted(
        {
            reviewer
            for reviewer, normalized in zip(reviewers, normalized_reviewers)
            if normalized_reviewers.count(normalized) > 1
        },
        key=str.casefold,
    )
    if duplicates:
        raise ValueError(f"Duplicate GitHub username(s): {', '.join(duplicates)}")

    return reviewers


def select_reviewer(reviewers_value: str, commit_sha: str) -> str:
    reviewers = parse_reviewers(reviewers_value)
    if not COMMIT_SHA.fullmatch(commit_sha):
        raise ValueError("OpenAPI commit SHA must be a 40-character hexadecimal value")

    return reviewers[int(commit_sha, 16) % len(reviewers)]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("reviewers", help="Comma-separated GitHub usernames")
    parser.add_argument("commit_sha", help="Full OpenAPI commit SHA")
    parser.add_argument("output_file", type=Path, help="GitHub Actions output file")
    args = parser.parse_args()

    try:
        reviewer = select_reviewer(args.reviewers, args.commit_sha)
    except ValueError as error:
        parser.error(str(error))

    with args.output_file.open("a") as output:
        output.write(f"reviewer={reviewer}\n")


if __name__ == "__main__":
    main()
