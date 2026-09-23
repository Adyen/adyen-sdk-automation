#!/usr/bin/env python3

"""Compare the published OpenAPI specs with the SDK service catalog.

config/services.json is an allowlist: the Gradle build and the CI matrix only act
on the services it names. Nothing in that flow looks at the specs it does *not*
name, so two kinds of drift stay invisible until an integrator reports them:

* a spec is published to Adyen/adyen-openapi and reaches no SDK at all;
* a catalog entry stays pinned below the newest published spec version, so the
  service looks complete while missing every endpoint added since.

This check diffs the two sides. Gaps that were reviewed and accepted live in
config/spec-coverage-baseline.json, so only unreviewed drift fails the run. A
version pin is accepted for one specific version, which keeps the baseline from
muting the next version bump.
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).parents[2]
DEFAULT_CATALOG = REPO_ROOT / "config" / "services.json"
DEFAULT_BASELINE = REPO_ROOT / "config" / "spec-coverage-baseline.json"
# Mirrors the `specs` Gradle task, which clones Adyen/adyen-openapi into schema/.
DEFAULT_SPECS = REPO_ROOT / "schema" / "json"

# Mirrors Service.filename in buildSrc: "<spec>-v<version>.json".
SPEC_FILENAME = re.compile(r"^(?P<spec>.+)-v(?P<version>\d+)\.json$")

UNREVIEWED_REASON = "UNREVIEWED: record why this spec has no SDK coverage"

SUPPORTED_BASELINE_FIELDS = {"uncoveredSpecs", "pinnedVersions"}
SUPPORTED_UNCOVERED_FIELDS = {"reason", "ticket"}
SUPPORTED_PINNED_FIELDS = {"acknowledgedVersion", "reason", "ticket"}

UNCOVERED = "uncovered-spec"
BEHIND = "outdated-version"
MISSING = "missing-spec"
STALE = "stale-baseline"


class BaselineError(Exception):
    """The baseline file itself is malformed, so no finding can be trusted."""


@dataclass(frozen=True)
class Finding:
    kind: str
    spec: str
    detail: str
    accepted: bool = False
    reason: str = ""
    ticket: str = ""

    @property
    def label(self) -> str:
        return f"{self.spec}: {self.detail}"

    @property
    def note(self) -> str:
        if not self.accepted:
            return ""
        return f"{self.reason} ({self.ticket})" if self.ticket else self.reason


def spec_name(service: dict) -> str:
    """Return the source spec name, defaulting to "<name>Service" as Gradle does."""
    return service.get("spec") or f"{service['name']}Service"


def discover_specs(specs_dir: Path) -> dict[str, list[int]]:
    """Map every published spec name to its sorted list of versions."""
    if not specs_dir.is_dir():
        raise FileNotFoundError(
            f"No spec directory at {specs_dir}. Run `./gradlew specs` to clone Adyen/adyen-openapi, "
            f"or pass --specs."
        )

    families: dict[str, list[int]] = {}
    for path in sorted(specs_dir.glob("*.json")):
        match = SPEC_FILENAME.match(path.name)
        if match:
            families.setdefault(match["spec"], []).append(int(match["version"]))

    if not families:
        raise FileNotFoundError(f"No <Name>-v<N>.json specs found in {specs_dir}")

    return {name: sorted(versions) for name, versions in families.items()}


def load_catalog(catalog_path: Path) -> list[dict]:
    with catalog_path.open() as catalog_file:
        return json.load(catalog_file)["services"]


def load_baseline(baseline_path: Path) -> dict:
    """Read the accepted gaps, tolerating an absent file but not a malformed one."""
    if not baseline_path.exists():
        return {"uncoveredSpecs": {}, "pinnedVersions": {}}

    with baseline_path.open() as baseline_file:
        baseline = json.load(baseline_file)

    unknown = set(baseline) - SUPPORTED_BASELINE_FIELDS
    if unknown:
        raise BaselineError(f"Unknown baseline field(s): {', '.join(sorted(unknown))}")

    uncovered = baseline.get("uncoveredSpecs", {})
    pinned = baseline.get("pinnedVersions", {})
    for section, entries, supported in (
        ("uncoveredSpecs", uncovered, SUPPORTED_UNCOVERED_FIELDS),
        ("pinnedVersions", pinned, SUPPORTED_PINNED_FIELDS),
    ):
        if not isinstance(entries, dict):
            raise BaselineError(f"{section} must be an object keyed by spec name")
        for spec, entry in entries.items():
            if not isinstance(entry, dict):
                raise BaselineError(f"{section}.{spec} must be an object")
            unknown = set(entry) - supported
            if unknown:
                raise BaselineError(f"Unknown field(s) in {section}.{spec}: {', '.join(sorted(unknown))}")
            # An entry without a reason is an unexplained mute, which is what this check exists to prevent.
            if not isinstance(entry.get("reason"), str) or not entry["reason"].strip():
                raise BaselineError(f"{section}.{spec} must have a non-empty reason")

    for spec, entry in pinned.items():
        version = entry.get("acknowledgedVersion")
        if not isinstance(version, int) or isinstance(version, bool) or version <= 0:
            raise BaselineError(f"pinnedVersions.{spec}.acknowledgedVersion must be a positive int")

    return {"uncoveredSpecs": uncovered, "pinnedVersions": pinned}


def evaluate(specs: dict[str, list[int]], services: list[dict], baseline: dict) -> list[Finding]:
    """Diff the published specs against the catalog and apply the baseline."""
    findings: list[Finding] = []
    accepted_uncovered = baseline["uncoveredSpecs"]
    accepted_pins = baseline["pinnedVersions"]
    covered = {spec_name(service): service for service in services}

    for spec, versions in sorted(specs.items()):
        newest = max(versions)
        if spec not in covered:
            entry = accepted_uncovered.get(spec, {})
            findings.append(
                Finding(
                    kind=UNCOVERED,
                    spec=spec,
                    detail=f"published up to v{newest}, absent from the catalog, so no SDK exposes it",
                    accepted=spec in accepted_uncovered,
                    reason=entry.get("reason", ""),
                    ticket=entry.get("ticket", ""),
                )
            )
            continue

        pinned = covered[spec]["version"]
        if pinned < newest:
            entry = accepted_pins.get(spec, {})
            # The pin is accepted for one version only, so the next release fails again.
            accepted = entry.get("acknowledgedVersion") == newest
            findings.append(
                Finding(
                    kind=BEHIND,
                    spec=spec,
                    detail=f"catalog pins v{pinned} while v{newest} is published",
                    accepted=accepted,
                    reason=entry.get("reason", ""),
                    ticket=entry.get("ticket", ""),
                )
            )

    # A pinned spec file that does not exist breaks generation at configuration time,
    # so it is always a failure and cannot be accepted by the baseline.
    for service in services:
        spec = spec_name(service)
        if service["version"] not in specs.get(spec, []):
            findings.append(
                Finding(
                    kind=MISSING,
                    spec=spec,
                    detail=f"catalog pins v{service['version']}, which is not published "
                    f"(available: {specs.get(spec) or 'none'})",
                )
            )

    findings.extend(stale_baseline_findings(specs, covered, baseline))
    return findings


def stale_baseline_findings(specs: dict[str, list[int]], covered: dict[str, dict], baseline: dict) -> list[Finding]:
    """Report accepted gaps that no longer exist, so the baseline gets pruned."""
    findings: list[Finding] = []

    for spec in sorted(baseline["uncoveredSpecs"]):
        if spec in covered:
            findings.append(
                Finding(kind=STALE, spec=spec, detail="now in the catalog, remove it from uncoveredSpecs")
            )
        elif spec not in specs:
            findings.append(
                Finding(kind=STALE, spec=spec, detail="no longer published, remove it from uncoveredSpecs")
            )

    for spec in sorted(baseline["pinnedVersions"]):
        if spec not in covered:
            findings.append(
                Finding(kind=STALE, spec=spec, detail="not in the catalog, remove it from pinnedVersions")
            )
        elif covered[spec]["version"] >= max(specs.get(spec, [0])):
            findings.append(
                Finding(kind=STALE, spec=spec, detail="no longer behind, remove it from pinnedVersions")
            )

    return findings


def build_baseline(findings: list[Finding], specs: dict[str, list[int]], previous: dict) -> dict:
    """Return a baseline accepting today's gaps, keeping the reasons already recorded."""
    uncovered: dict[str, dict] = {}
    pinned: dict[str, dict] = {}

    for finding in findings:
        if finding.kind == UNCOVERED:
            existing = previous["uncoveredSpecs"].get(finding.spec, {})
            uncovered[finding.spec] = {"reason": existing.get("reason") or UNREVIEWED_REASON}
            if existing.get("ticket"):
                uncovered[finding.spec]["ticket"] = existing["ticket"]
        elif finding.kind == BEHIND:
            existing = previous["pinnedVersions"].get(finding.spec, {})
            pinned[finding.spec] = {
                "acknowledgedVersion": max(specs[finding.spec]),
                "reason": existing.get("reason") or UNREVIEWED_REASON,
            }
            if existing.get("ticket"):
                pinned[finding.spec]["ticket"] = existing["ticket"]

    return {
        "uncoveredSpecs": _keep_recorded_order(uncovered, previous["uncoveredSpecs"]),
        "pinnedVersions": _keep_recorded_order(pinned, previous["pinnedVersions"]),
    }


def _keep_recorded_order(entries: dict[str, dict], previous: dict[str, dict]) -> dict[str, dict]:
    """Preserve the order of entries already recorded, appending new ones at the end.

    The committed baseline is grouped by theme rather than sorted, so rebuilding it in
    finding order would rewrite every line and bury the entries that actually changed.
    """
    kept = {spec: entries[spec] for spec in previous if spec in entries}
    return {**kept, **{spec: entry for spec, entry in entries.items() if spec not in kept}}


def render_text(findings: list[Finding], specs: dict[str, list[int]], services: list[dict]) -> str:
    new = [finding for finding in findings if not finding.accepted]
    accepted = [finding for finding in findings if finding.accepted]

    lines = [
        f"Compared {len(specs)} published spec(s) with {len(services)} catalog entr(ies).",
        "",
    ]

    if new:
        lines.append(f"Unreviewed drift ({len(new)}):")
        lines.extend(f"  [{finding.kind}] {finding.label}" for finding in new)
    else:
        lines.append("Unreviewed drift: none.")

    if accepted:
        lines += ["", f"Accepted gaps ({len(accepted)}):"]
        lines.extend(f"  [{finding.kind}] {finding.label} -- {finding.note}" for finding in accepted)

    if new:
        lines += [
            "",
            "Resolve each item by either adding the service to config/services.json (or bumping its",
            "version), or recording the decision in config/spec-coverage-baseline.json.",
        ]

    return "\n".join(lines)


def render_markdown(findings: list[Finding], specs: dict[str, list[int]], services: list[dict]) -> str:
    new = [finding for finding in findings if not finding.accepted]
    accepted = [finding for finding in findings if finding.accepted]

    lines = ["## SDK spec coverage", ""]
    lines.append(f"Compared **{len(specs)}** published specs with **{len(services)}** catalog entries.")
    lines.append("")

    if new:
        lines += [
            f"### Unreviewed drift ({len(new)})",
            "",
            "| Spec | Finding | Detail |",
            "| --- | --- | --- |",
        ]
        lines += [f"| `{finding.spec}` | {finding.kind} | {finding.detail} |" for finding in new]
        lines += [
            "",
            "Add the service to `config/services.json` (or bump its version), "
            "or record the decision in `config/spec-coverage-baseline.json`.",
            "",
        ]
    else:
        lines += ["No unreviewed drift.", ""]

    if accepted:
        lines += [
            f"<details><summary>Accepted gaps ({len(accepted)})</summary>",
            "",
            "| Spec | Finding | Reason |",
            "| --- | --- | --- |",
        ]
        lines += [f"| `{finding.spec}` | {finding.kind} | {finding.note} |" for finding in accepted]
        lines += ["", "</details>", ""]

    return "\n".join(lines)


def annotate(findings: list[Finding]) -> None:
    """Emit GitHub Actions annotations so drift surfaces on the run, not only in the log."""
    if not os.environ.get("GITHUB_ACTIONS"):
        return
    for finding in findings:
        if not finding.accepted:
            print(f"::error title=SDK spec coverage ({finding.kind})::{finding.label}")


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG, help="Path to config/services.json")
    parser.add_argument("--specs", type=Path, default=DEFAULT_SPECS, help="Directory holding the published specs")
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE, help="Path to the accepted-gaps baseline")
    parser.add_argument("--summary", type=Path, help="Append a Markdown report to this file, e.g. $GITHUB_STEP_SUMMARY")
    parser.add_argument(
        "--write-baseline",
        action="store_true",
        help="Accept every current gap by rewriting the baseline, keeping the reasons already recorded",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    try:
        specs = discover_specs(args.specs)
        baseline = load_baseline(args.baseline)
    except (FileNotFoundError, BaselineError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    services = load_catalog(args.catalog)
    findings = evaluate(specs, services, baseline)

    if args.write_baseline:
        args.baseline.write_text(json.dumps(build_baseline(findings, specs, baseline), indent=2) + "\n")
        print(f"Wrote {args.baseline}. Replace every '{UNREVIEWED_REASON}' with a real decision.")
        return 0

    print(render_text(findings, specs, services))
    if args.summary:
        with args.summary.open("a") as summary_file:
            summary_file.write(render_markdown(findings, specs, services) + "\n")
    annotate(findings)

    return 1 if any(not finding.accepted for finding in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
