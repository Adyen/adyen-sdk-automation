"""Shared OpenAPI spec, catalog, and baseline coverage logic."""

import json
import re
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).parents[2]
DEFAULT_CATALOG = REPO_ROOT / "config" / "services.json"
DEFAULT_BASELINE = REPO_ROOT / "config" / "spec-coverage-baseline.json"
DEFAULT_SPECS = REPO_ROOT / "schema" / "json"

SPEC_FILENAME = re.compile(r"^(?P<spec>.+)-v(?P<version>\d+)\.json$")

KNOWN_PROJECTS = {"java", "php", "node", "python", "ruby", "go", "dotnet"}
SUPPORTED_SERVICE_FIELDS = {
    "name", "version", "spec", "small", "group", "projects", "excludedProjects",
}

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
    service_name: str = ""
    baseline_section: str = ""

    @property
    def label(self) -> str:
        return f"{self.spec}: {self.detail}"

    @property
    def reviewed(self) -> bool:
        return self.accepted and not self.reason.lstrip().upper().startswith("UNREVIEWED:")

    @property
    def note(self) -> str:
        if not self.accepted:
            return ""
        return f"{self.reason} ({self.ticket})" if self.ticket else self.reason


def spec_name(service: dict) -> str:
    """Return the source spec name, defaulting to "<name>Service" as Gradle does."""
    return service.get("spec") or f"{service['name']}Service"


def discover_specs(specs_dir: Path, *, public_only: bool = False) -> dict[str, list[int]]:
    """Map spec names to versions, optionally excluding explicitly non-public specs."""
    if not specs_dir.is_dir():
        raise FileNotFoundError(
            f"No spec directory at {specs_dir}. Run `./gradlew specs` to clone Adyen/adyen-openapi, "
            f"or pass --specs."
        )

    families: dict[str, list[int]] = {}
    found_spec = False
    for path in sorted(specs_dir.glob("*.json")):
        match = SPEC_FILENAME.match(path.name)
        if match:
            found_spec = True
            if public_only:
                document = json.loads(path.read_text())
                if document.get("info", {}).get("x-publicVersion") is False:
                    continue
            families.setdefault(match["spec"], []).append(int(match["version"]))

    if not found_spec:
        raise FileNotFoundError(f"No <Name>-v<N>.json specs found in {specs_dir}")

    return {name: sorted(versions) for name, versions in families.items()}


def load_catalog(catalog_path: Path) -> list[dict]:
    """Read a catalog and validate the service-matrix contract before using it."""
    with catalog_path.open() as catalog_file:
        catalog = json.load(catalog_file)

    if not isinstance(catalog, dict) or set(catalog) != {"services"}:
        raise ValueError("Catalog must be an object containing only the services field")
    services = catalog["services"]
    if not isinstance(services, list) or not services:
        raise ValueError("Catalog services must be a non-empty list")

    service_ids = set()
    for index, service in enumerate(services):
        label = f"services[{index}]"
        if not isinstance(service, dict):
            raise ValueError(f"{label} must be an object")
        unknown = set(service) - SUPPORTED_SERVICE_FIELDS
        if unknown:
            raise ValueError(f"Unknown field(s) in {label}: {', '.join(sorted(unknown))}")
        name = service.get("name")
        if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9]*", name):
            raise ValueError(f"{label}.name must start with an ASCII letter and be alphanumeric")
        if name.lower() in service_ids:
            raise ValueError(f"Duplicate service id: {name.lower()}")
        service_ids.add(name.lower())
        version = service.get("version")
        if type(version) is not int or version <= 0:
            raise ValueError(f"{label}.version must be a positive int")
        if "spec" in service and not isinstance(service["spec"], str):
            raise ValueError(f"{label}.spec must be a string")
        if "small" in service and not isinstance(service["small"], bool):
            raise ValueError(f"{label}.small must be a boolean")
        if "projects" in service and "excludedProjects" in service:
            raise ValueError(f"{label} cannot define both projects and excludedProjects")
        for field in ("projects", "excludedProjects"):
            if field not in service:
                continue
            projects = service[field]
            if not isinstance(projects, list) or any(
                not isinstance(project, str) or project not in KNOWN_PROJECTS
                for project in projects
            ):
                raise ValueError(f"{label}.{field} must be a list of known projects")
            if field == "projects" and not projects:
                raise ValueError(f"{label}.projects must not be empty")

    return services


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
            # An entry without a reason is an unexplained mute.
            if not isinstance(entry.get("reason"), str) or not entry["reason"].strip():
                raise BaselineError(f"{section}.{spec} must have a non-empty reason")

    for spec, entry in pinned.items():
        version = entry.get("acknowledgedVersion")
        if not isinstance(version, int) or isinstance(version, bool) or version <= 0:
            raise BaselineError(f"pinnedVersions.{spec}.acknowledgedVersion must be a positive int")

    return {"uncoveredSpecs": uncovered, "pinnedVersions": pinned}


def evaluate(
    specs: dict[str, list[int]],
    services: list[dict],
    baseline: dict,
    available_specs: dict[str, list[int]] | None = None,
) -> list[Finding]:
    """Diff published specs against the catalog and apply the baseline."""
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
                    detail=f"published up to v{newest}, absent from the generation catalog",
                    accepted=spec in accepted_uncovered,
                    reason=entry.get("reason", ""),
                    ticket=entry.get("ticket", ""),
                )
            )
            continue

        service = covered[spec]
        pinned = service["version"]
        if pinned < newest:
            entry = accepted_pins.get(spec, {})
            findings.append(
                Finding(
                    kind=BEHIND,
                    spec=spec,
                    detail=f"catalog pins v{pinned} while v{newest} is published",
                    accepted=entry.get("acknowledgedVersion") == newest,
                    reason=entry.get("reason", ""),
                    ticket=entry.get("ticket", ""),
                    service_name=service["name"],
                )
            )

    # A missing pinned file prevents generation, even if a baseline covers the family.
    available = specs if available_specs is None else available_specs
    for service in services:
        spec = spec_name(service)
        if service["version"] not in available.get(spec, []):
            findings.append(
                Finding(
                    kind=MISSING,
                    spec=spec,
                    detail=f"catalog pins v{service['version']}, which is not published "
                    f"(available: {available.get(spec) or 'none'})",
                    service_name=service["name"],
                )
            )

    findings.extend(stale_baseline_findings(specs, covered, baseline))
    return findings


def stale_baseline_findings(
    specs: dict[str, list[int]],
    covered: dict[str, dict],
    baseline: dict,
) -> list[Finding]:
    """Report accepted gaps that no longer exist, so the baseline gets pruned."""
    findings: list[Finding] = []

    for spec in sorted(baseline["uncoveredSpecs"]):
        entry = baseline["uncoveredSpecs"][spec]
        if spec in covered:
            detail = "now in the catalog, remove it from uncoveredSpecs"
        elif spec not in specs:
            detail = "no longer published, remove it from uncoveredSpecs"
        else:
            continue
        findings.append(
            Finding(
                kind=STALE,
                spec=spec,
                detail=detail,
                reason=entry.get("reason", ""),
                ticket=entry.get("ticket", ""),
                baseline_section="uncoveredSpecs",
            )
        )

    for spec in sorted(baseline["pinnedVersions"]):
        entry = baseline["pinnedVersions"][spec]
        if spec not in covered:
            detail = "not in the catalog, remove it from pinnedVersions"
        elif covered[spec]["version"] >= max(specs.get(spec, [0])):
            detail = "no longer behind, remove it from pinnedVersions"
        else:
            continue
        findings.append(
            Finding(
                kind=STALE,
                spec=spec,
                detail=detail,
                reason=entry.get("reason", ""),
                ticket=entry.get("ticket", ""),
                baseline_section="pinnedVersions",
            )
        )

    return findings


