#!/usr/bin/env python3

"""Propose catalog entries for published specs that no SDK covers.

check_spec_coverage.py reports the gap. This turns each `uncovered-spec` finding
into a concrete edit of config/services.json, so a new API reaches review as a
diff instead of a line in a log.

Only the mechanical part is automated. The target service name is a product
decision: 17 of the 30 existing entries have a name that cannot be derived from
their spec name, and `small`, `projects` and `excludedProjects` encode per-library
capability decisions. Everything this script writes is therefore a proposal for a
human to correct, and it deliberately never touches a spec that already has a
recorded decision in config/spec-coverage-baseline.json. Removing a spec from the
baseline is how you ask for it to be proposed.
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import check_spec_coverage as checker

# Mirrors test_services_catalog.py, which rejects any other name on every PR.
VALID_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9]*$")

CATALOG_INDENT = "    "


@dataclass(frozen=True)
class Proposal:
    spec: str
    name: str
    version: int
    # The rule that did not win, when the two disagree. Shown for the reviewer to choose from.
    alternative: str = ""

    @property
    def needs_explicit_spec(self) -> bool:
        """Gradle derives "<name>Service", so `spec` is only needed when it differs."""
        return self.spec != f"{self.name}Service"

    @property
    def entry(self) -> dict:
        entry = {"name": self.name}
        if self.needs_explicit_spec:
            entry["spec"] = self.spec
        entry["version"] = self.version
        return entry

    @property
    def line(self) -> str:
        fields = ", ".join(f'"{key}": {json.dumps(value)}' for key, value in self.entry.items())
        return f"{CATALOG_INDENT}{{ {fields} }}"


@dataclass
class Plan:
    proposals: list[Proposal] = field(default_factory=list)
    skipped: list[tuple[str, str]] = field(default_factory=list)


def derive_name(spec: str) -> str:
    """Guess the SDK service name from the spec name, following catalog precedent.

    Webhook specs are named "<Domain>Webhooks" with the BalancePlatform prefix dropped,
    and plain services drop the "Service" suffix. Measured against the 30 current entries
    this is right 23 times.
    """
    if spec.endswith("NotificationService"):
        return f"{spec.removesuffix('NotificationService')}Webhooks"
    if spec.endswith("Notification"):
        domain = spec.removesuffix("Notification").removeprefix("BalancePlatform")
        return f"{domain}Webhooks"
    if spec.endswith("Service"):
        return spec.removesuffix("Service")
    return spec


def name_from_title(title: str) -> str:
    """Guess the SDK service name from info.title.

    Measured against the 30 current entries this is right 25 times, two more than the
    filename rule, and it fails on different entries. Each substitution below fixes a
    real family of misses: the "Adyen" prefix (8 entries such as "Adyen Checkout API"),
    the deprecation marker, and the singular "webhook" ("Balance webhook" is BalanceWebhooks).
    """
    text = re.sub(r"\(deprecated\)", "", title, flags=re.IGNORECASE)
    text = re.sub(r"^\s*Adyen\s+", "", text)
    text = re.sub(r"\b(API|APIs)\b", "", text)
    text = re.sub(r"\bwebhook\b", "webhooks", text, flags=re.IGNORECASE)
    text = re.sub(r"[^A-Za-z0-9 ]", " ", text)
    return "".join(word[:1].upper() + word[1:] for word in text.split())


def read_spec_info(specs_dir: Path, spec: str, version: int) -> dict:
    """Return the `info` object of one spec file, or an empty dict when it cannot be read."""
    try:
        with (specs_dir / f"{spec}-v{version}.json").open() as spec_file:
            return json.load(spec_file).get("info", {})
    except (OSError, json.JSONDecodeError, AttributeError):
        return {}


def public_version(specs_dir: Path, spec: str, versions: list[int]) -> int:
    """Return the newest version that is not explicitly marked non-public.

    `x-publicVersion` is absent from 21 specs and true on the rest, so only an explicit
    false excludes a version. Requiring a true value would reject every spec that omits it.
    """
    for version in sorted(versions, reverse=True):
        if read_spec_info(specs_dir, spec, version).get("x-publicVersion") is not False:
            return version
    return max(versions)


def candidate_names(specs_dir: Path, spec: str, version: int) -> tuple[str, str]:
    """Return the preferred name and the runner-up, in that order.

    The title rule has the better record, so it leads when it produces a usable name. The
    filename rule is kept as the alternative because the two fail on different specs: for
    "Account-to-Account (A2A) payments API" the title yields AccountToAccountA2APayments
    while the filename yields the far better A2APayments.
    """
    from_filename = derive_name(spec)
    title = read_spec_info(specs_dir, spec, version).get("title", "")
    from_title = name_from_title(title) if title else ""

    if not from_title or not VALID_NAME.match(from_title):
        return from_filename, ""
    if from_title.lower() == from_filename.lower():
        return from_title, ""
    return from_title, from_filename


def build_plan(
    findings: list[checker.Finding],
    specs: dict[str, list[int]],
    services: list[dict],
    specs_dir: Path,
) -> Plan:
    """Turn unreviewed uncovered-spec findings into proposals, skipping the unsafe ones."""
    plan = Plan()
    taken = {service["name"].lower() for service in services}

    for finding in findings:
        if finding.kind != checker.UNCOVERED or finding.accepted:
            continue

        version = public_version(specs_dir, finding.spec, specs[finding.spec])
        name, alternative = candidate_names(specs_dir, finding.spec, version)
        if not VALID_NAME.match(name):
            plan.skipped.append((finding.spec, f"derived name `{name}` is not alphanumeric, needs a manual name"))
            continue
        if name.lower() in taken:
            plan.skipped.append((finding.spec, f"derived name `{name}` collides with an existing entry"))
            continue

        taken.add(name.lower())
        plan.proposals.append(
            Proposal(spec=finding.spec, name=name, version=version, alternative=alternative)
        )

    return plan


def insert_entries(catalog_text: str, proposals: list[Proposal]) -> str:
    """Append entries to the services array, leaving the rest of the file byte-identical.

    The catalog is hand-formatted with one entry per line and blank lines between groups,
    so it is edited as text. Reserialising it would reformat all 30 entries and bury the
    one line a reviewer needs to look at.
    """
    if not proposals:
        return catalog_text

    lines = catalog_text.split("\n")
    closing = next((index for index in reversed(range(len(lines))) if lines[index].rstrip() == "  ]"), None)
    if closing is None:
        raise ValueError("Could not find the end of the services array in the catalog")

    last_entry = next((index for index in reversed(range(closing)) if lines[index].strip()), None)
    if last_entry is None:
        raise ValueError("Could not find an existing entry in the services array")
    if not lines[last_entry].rstrip().endswith(","):
        lines[last_entry] = lines[last_entry].rstrip() + ","

    # A blank line keeps the proposals visually separate from the curated groups above.
    block = [""] + [proposal.line + "," for proposal in proposals]
    block[-1] = block[-1].rstrip(",")

    return "\n".join(lines[:closing] + block + lines[closing:])


def render_pr_body(plan: Plan) -> str:
    if not plan.proposals and not plan.skipped:
        return "No published spec is missing a catalog entry.\n"

    lines = [
        "Specs published in [adyen-openapi](https://github.com/Adyen/adyen-openapi) that no SDK covers.",
        "",
        "`version` is the newest published version that is not marked non-public, and `spec` comes "
        "from the filename, so both should be correct. **Every `name` is a guess.** It is taken from "
        "`info.title`, which reproduces 25 of the 30 existing entries; where the spec filename "
        "suggests something different, that alternative is listed for you to pick. Neither rule can "
        "know a product rename such as `TerminalAPI` becoming `Tapi`.",
        "",
    ]

    if plan.proposals:
        lines += ["| Spec | Proposed name | Alternative | Version |", "| --- | --- | --- | --- |"]
        lines += [
            f"| [`{proposal.spec}`](https://github.com/Adyen/adyen-openapi/blob/main/json/"
            f"{proposal.spec}-v{proposal.version}.json) | `{proposal.name}` | "
            f"{f'`{proposal.alternative}`' if proposal.alternative else '-'} | {proposal.version} |"
            for proposal in plan.proposals
        ]
        lines += [
            "",
            "Before merging, for each entry:",
            "",
            "- [ ] Confirm the API should ship in the SDKs at all. If not, close this and record the "
            "decision in `config/spec-coverage-baseline.json` instead.",
            "- [ ] Confirm or correct `name`, and drop `spec` if it becomes `<name>Service`.",
            "- [ ] Add `group` for the README tables.",
            "- [ ] Decide `small` (a self-contained generated file, used by 9 of 30 entries).",
            "- [ ] Decide `projects` or `excludedProjects` if any library cannot support it.",
            "",
            "Merging fans out to every library: `config/services.json` is a generation-affecting path, "
            "so `Update SDKs` will open a per-service pull request in each `adyen-*-api-library`.",
            "",
        ]

    if plan.skipped:
        lines += ["Needs a name chosen by hand:", ""]
        lines += [f"- `{spec}`: {reason}" for spec, reason in plan.skipped]
        lines += [""]

    return "\n".join(lines)


def render_text(plan: Plan) -> str:
    if not plan.proposals and not plan.skipped:
        return "No published spec is missing a catalog entry."

    lines = []
    if plan.proposals:
        lines.append(f"Proposing {len(plan.proposals)} catalog entr(ies):")
        lines += [
            proposal.line + (f"   (alternative name: {proposal.alternative})" if proposal.alternative else "")
            for proposal in plan.proposals
        ]
    if plan.skipped:
        lines += ["", "Skipped:"]
        lines += [f"  {spec}: {reason}" for spec, reason in plan.skipped]
    return "\n".join(lines)


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--catalog", type=Path, default=checker.DEFAULT_CATALOG, help="Path to config/services.json")
    parser.add_argument("--specs", type=Path, default=checker.DEFAULT_SPECS, help="Directory holding the published specs")
    parser.add_argument("--baseline", type=Path, default=checker.DEFAULT_BASELINE, help="Path to the accepted-gaps baseline")
    parser.add_argument("--write", action="store_true", help="Apply the proposals to the catalog")
    parser.add_argument("--pr-body", type=Path, help="Write the pull request body to this file")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    try:
        specs = checker.discover_specs(args.specs)
        baseline = checker.load_baseline(args.baseline)
    except (FileNotFoundError, checker.BaselineError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    services = checker.load_catalog(args.catalog)
    plan = build_plan(checker.evaluate(specs, services, baseline), specs, services, args.specs)

    print(render_text(plan))

    if args.write and plan.proposals:
        catalog_text = args.catalog.read_text()
        args.catalog.write_text(insert_entries(catalog_text, plan.proposals))
        print(f"Updated {args.catalog}")

    if args.pr_body:
        args.pr_body.write_text(render_pr_body(plan))

    return 0


if __name__ == "__main__":
    sys.exit(main())
