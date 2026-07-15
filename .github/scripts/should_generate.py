#!/usr/bin/env python3

"""Classify whether a push may change generated SDK code.

The generation workflow runs for changes to generator inputs and build
infrastructure, while documentation and test-only updates are skipped to avoid
unnecessary SDK pull requests. Ambiguous changes deliberately generate as a
safe fallback, and the result is written in GitHub Actions output format.
"""

import argparse
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

TEST_DEPENDENCY = re.compile(r"\s*(?:testImplementation|testRuntimeOnly)\(")


@dataclass(frozen=True)
class Decision:
    should_generate: bool
    reason: str


def git_output(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def is_test_dependency_only(repo: Path, before_sha: str, after_sha: str) -> bool:
    diff = git_output(repo, "diff", "--unified=0", before_sha, after_sha, "--", "buildSrc/build.gradle.kts")
    changed_lines = [
        line[1:]
        for line in diff.splitlines()
        if line.startswith(("+", "-")) and not line.startswith(("+++ ", "--- "))
    ]
    return bool(changed_lines) and all(TEST_DEPENDENCY.match(line) for line in changed_lines)


def is_missing_base_commit(repo: Path, before_sha: str) -> bool:
    if re.fullmatch(r"0+", before_sha):
        return True

    return subprocess.run(
        ["git", "cat-file", "-e", f"{before_sha}^{{commit}}"],
        cwd=repo,
        capture_output=True,
        check=False,
    ).returncode != 0


def is_non_generation_file(path: str) -> bool:
    return (
        path in {"LICENSE", ".github/CODEOWNERS"}
        or path.endswith(".md")
        or path.startswith("buildSrc/src/test/")
        or path.startswith(".github/scripts/test_")
    )


def classify_changes(before_sha: str, after_sha: str, repo: Path) -> Decision:
    """Return the safe generation decision for the commit range."""
    if is_missing_base_commit(repo, before_sha):
        return Decision(True, "missing-base-commit")

    changed_files = git_output(repo, "diff", "--name-only", before_sha, after_sha).splitlines()
    if not changed_files:
        return Decision(False, "no-changes")

    for path in changed_files:
        if is_non_generation_file(path):
            continue
        if path == "buildSrc/build.gradle.kts" and is_test_dependency_only(repo, before_sha, after_sha):
            continue
        return Decision(True, f"generation-affecting-change:{path}")

    return Decision(False, "non-generation-changes-only")


def write_output(decision: Decision, output_file: Path) -> None:
    with output_file.open("a") as output:
        output.write(f"should_generate={str(decision.should_generate).lower()}\n")
        output.write(f"reason={decision.reason}\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("before_sha")
    parser.add_argument("after_sha")
    parser.add_argument("output_file", type=Path)
    args = parser.parse_args()

    write_output(classify_changes(args.before_sha, args.after_sha, Path.cwd()), args.output_file)


if __name__ == "__main__":
    main()
