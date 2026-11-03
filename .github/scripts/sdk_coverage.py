#!/usr/bin/env python3

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import check_spec_coverage as checker


ROOT = Path(__file__).resolve().parents[2]

PROJECTS = [
    "java",
    "node",
    "python",
    "php",
    "ruby",
    "go",
    "dotnet",
]

PROJECT_LABELS = {
    "java": "Java",
    "node": "Node",
    "python": "Python",
    "php": "PHP",
    "ruby": "Ruby",
    "go": "Go",
    "dotnet": ".NET",
}

SOURCE_EXTENSIONS = {
    ".java",
    ".ts",
    ".py",
    ".php",
    ".rb",
    ".go",
    ".cs",
}

SOURCE_ROOTS = {
    "java": ("src/main/java", ".java"),
    "node": ("src", ".ts"),
    "python": ("Adyen", ".py"),
    "php": ("src/Adyen", ".php"),
    "ruby": ("lib", ".rb"),
    "go": ("src", ".go"),
    "dotnet": ("Adyen", ".cs"),
}

SOURCE_DECLARATION = re.compile(
    r"^[ \t]*(?:(?:export|public|abstract|final|partial|declare|sealed|static)\s+)*"
    r"(?:class|interface|enum|type)\s+([A-Za-z_]\w*)",
    re.MULTILINE,
)
UNSUPPORTED_NOT_ASSESSED = "Unsupported; presence not assessed"

VERSION_PATTERNS = {
    "java": re.compile(
        r"The version of the OpenAPI document:\s*v?(\d+)",
        re.IGNORECASE,
    ),
    "node": re.compile(
        r"The version of the OpenAPI document:\s*v?(\d+)",
        re.IGNORECASE,
    ),
    "python": re.compile(
        r'baseUrl\s*=\s*["\'][^"\']+/v(\d+)["\']',
        re.IGNORECASE,
    ),
    "php": re.compile(
        r"The version of the OpenAPI document:\s*v?(\d+)",
        re.IGNORECASE,
    ),
    "ruby": re.compile(
        r"DEFAULT_VERSION\s*=\s*(\d+)",
        re.IGNORECASE,
    ),
    "go": re.compile(
        r"API version:\s*v?(\d+)",
        re.IGNORECASE,
    ),
    "dotnet": re.compile(
        r'(?:ApiVersion\s*=>\s*"'
        r"|The version of the OpenAPI document:"
        r'\s*v?)(\d+)"?',
        re.IGNORECASE,
    ),
}

# Service names that SDKs use for OpenAPI families that
# the generation catalog does not define. Families that
# predate generation ship under hand-written or
# historical names in the SDKs.
FAMILY_ALIASES = {
    "AccountService": [
        "MarketPay",
        "MarketPayAccount",
        "PlatformsAccount",
    ],
    "FundService": [
        "MarketPay",
        "MarketPayFund",
        "PlatformsFund",
    ],
    "HopService": [
        "MarketPay",
        "MarketPayHop",
        "MarketPayHostedOnboardingPage",
        "PlatformsHostedOnboardingPage",
    ],
        # Ruby ships the MarketPay facade with account,
    # fund, notification configuration, and hop services
    # only, so the generic MarketPay name is not evidence
    # for the notification payload models.
    "MarketPayNotificationService": [
        "MarketPayNotifications",
        "MarketPayWebhooks",
        "PlatformsNotifications",
    ],
    "NotificationConfigurationService": [
        "MarketPay",
        "MarketPayConfiguration",
        "MarketPayNotificationConfiguration",
        "PlatformsNotificationConfiguration",
    ],
    "TfmAPIService": [
        "PosTerminalManagement",
        "TerminalManagement",
    ],
}

# Aliases that apply to a single project. PHP ships the
# legacy notification configuration API as
# Service/Notification.php, while Java's
# model/notification and Node's typings/notification
# contain generic webhook models instead, so the name
# cannot be shared across projects.
FAMILY_PROJECT_ALIASES = {
    "TfmAPIService": {
        "python": ["Terminal"],
    },
    "NotificationConfigurationService": {
        "php": [
            "Notification",
        ],
    },
}

FORMAT_SETUP_COMMANDS = {
    "node": [
        "npm",
        "ci",
        "--legacy-peer-deps",
    ],
    "php": [
        "composer",
        "install",
        "--prefer-dist",
        "--no-progress",
    ],
}

FORMAT_COMMANDS = {
    "java": [
        [
            "mvn",
            "spotless:apply",
        ],
    ],
    "node": [
        [
            "npm",
            "run",
            "lint:fix",
        ],
    ],
    "python": [
        [
            "venv/bin/ruff",
            "format",
            "Adyen",
        ],
        [
            "venv/bin/ruff",
            "check",
            "--fix",
            "Adyen",
        ],
    ],
    "php": [
        [
            "composer",
            "run",
            "fmt",
        ],
    ],
    "go": [
        [
            "make",
            "fmt",
        ],
    ],
}

# Formatter executables that the format commands invoke
# through PATH instead of an absolute location.
FORMAT_PATH_PREREQUISITES = {
    "go": ["goimports"],
}


def run_command(command, cwd):
    """Run a shell command and capture everything it prints.

    The command runs inside `cwd`, and stderr is merged
    into stdout so the caller always sees one complete
    output string. A failing exit code is not raised;
    callers inspect the return code themselves.
    """

    return subprocess.run(
        command,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def has_format_action(repo):
    """Return whether an SDK defines a local formatting action.

    SDK repositories declare their formatter in
    .github/actions/format/action.yml. Only repositories
    with that file need formatting after generation.
    """

    return (
        repo
        / ".github/actions/format/action.yml"
    ).is_file()


def go_bin_directory():
    """Return the directory where Go installs commands.

    `go install` places binaries in the first entry of
    GOPATH, which is often missing from PATH on developer
    machines. Returns None when Go is unavailable.
    """

    try:
        result = run_command(
            ["go", "env", "GOPATH"],
            ROOT,
        )
    except FileNotFoundError:
        return None

    if result.returncode != 0:
        return None

    first_gopath = (
        result.stdout.strip().split(os.pathsep)[0]
    )

    if not first_gopath:
        return None

    return Path(first_gopath) / "bin"


def is_directory_on_path(directory):
    """Return whether a directory is on the current PATH.

    Entries are compared through realpath so symlinks
    and trailing slashes cannot hide a match.
    """

    for entry in os.environ.get(
            "PATH",
            "",
    ).split(os.pathsep):
        if not entry:
            continue

        if (
                os.path.realpath(entry)
                == os.path.realpath(str(directory))
        ):
            return True

    return False


def check_format_prerequisites(project):
    """Fail early when formatter commands cannot resolve.

    The Go Makefile installs goimports on first use, so a
    missing command is acceptable only when the directory
    it is installed into is on PATH. When the check fails
    it prints the exact export line that fixes the shell
    instead of letting every service fail later with a
    confusing formatter error.
    """

    names = FORMAT_PATH_PREREQUISITES.get(project, [])

    missing = [
        name
        for name in names
        if shutil.which(name) is None
    ]

    if not missing:
        return True

    bin_directory = go_bin_directory()

    if (
            bin_directory is not None
            and shutil.which("go") is not None
            and is_directory_on_path(bin_directory)
    ):
        # The build bootstraps the command and its
        # install directory is reachable.
        return True

    label = PROJECT_LABELS[project]

    print(
        f"Could not prepare {label} formatter"
    )
    print(
        f"{', '.join(missing)} is not on PATH, so "
        f"the {label} formatter will not run."
    )

    if bin_directory is None:
        print(
            "Install Go and make sure the directory "
            "where it installs commands "
            "((go env GOPATH)/bin) is on PATH."
        )
    else:
        installed = bin_directory / missing[0]

        if installed.exists():
            print(
                f"{missing[0]} is installed at "
                f"{installed}, but that directory "
                "is not on PATH. Re-run with it on "
                "PATH, for example:"
            )
        else:
            print(
                f"The {label} Makefile installs "
                f"{missing[0]} into {bin_directory} "
                "on first use, but that directory "
                "must be on PATH as well. Re-run "
                "with it on PATH, for example:"
            )

        print(
            f'  export PATH="{bin_directory}:$PATH"'
        )

    return False


def prepare_formatter(repo, project):
    """Install formatter dependencies once per SDK.

    Node and PHP need their toolchains present (npm ci,
    composer install) before any formatting, and Python
    gets a virtual environment with the dev extras.
    Projects without setup needs, such as Java, pass
    immediately. Returns False when the SDK cannot be
    formatted at all, letting the caller skip the project.
    """

    if not has_format_action(repo):
        return True

    if project not in FORMAT_COMMANDS:
        print(
            f"No local formatter command is configured "
            f"for {PROJECT_LABELS[project]}"
        )
        return False

    if not check_format_prerequisites(project):
        return False

    if project == "python":
        virtual_environment = repo / "venv"
        create_environment = run_command(
            [
                sys.executable,
                "-m",
                "venv",
                str(virtual_environment),
            ],
            repo,
        )

        if create_environment.returncode != 0:
            print(create_environment.stdout[-3000:])
            return False

        setup_command = [
            str(virtual_environment / "bin/python"),
            "-m",
            "pip",
            "install",
            "-e",
            ".[dev]",
        ]
    else:
        setup_command = FORMAT_SETUP_COMMANDS.get(project)

    if setup_command is None:
        return True

    print(
        f"Preparing {PROJECT_LABELS[project]} formatter..."
    )

    setup = run_command(setup_command, repo)

    if setup.returncode == 0:
        return True

    print(
        f"Could not prepare "
        f"{PROJECT_LABELS[project]} formatter"
    )
    print(setup.stdout[-3000:])
    return False


def parse_changed_paths(porcelain_lines):
    """Extract the changed paths from git status output.

    Understands modified files, new files, and renames
    (keeping the new name). Deleted paths are dropped
    because a formatter cannot process them, and quoted
    paths with special characters are unquoted.
    """

    paths = []

    for line in porcelain_lines:
        if not line:
            continue

        status = line[:2]
        path = line[3:]

        # Renames keep only the new path.
        if " -> " in path:
            path = path.split(" -> ")[1]

        # Deleted paths cannot be formatted.
        if "D" in status:
            continue

        path = path.strip('"').rstrip("/")

        if path:
            paths.append(path)

    return paths


def changed_repo_paths(repo):
    """Return the paths generation changed in an SDK repo.

    The repo is clean before generation runs, so every
    entry in git status is something generation touched.
    Returns None when git itself fails, and the caller
    then falls back to formatting the whole library.
    """

    status = run_command(
        [
            "git",
            "status",
            "--porcelain",
        ],
        repo,
    )

    if status.returncode != 0:
        # The changed paths are unknown, so the caller
        # falls back to formatting the whole library.
        return None

    return parse_changed_paths(
        status.stdout.splitlines()
    )


def scoped_format_command(project, changed_paths):
    """Build a formatter command limited to changed paths.

    Currently PHP only: the fmt composer script always
    walks the whole Service and Model trees, but phpcbf
    accepts explicit paths and finds the repository
    ruleset on its own, which makes a per-service format
    run take milliseconds instead of tens of seconds.
    Other projects return None and use their usual
    formatter command.
    """

    if project != "php":
        return None

    # The PHP fmt composer script always formats the
    # whole Service and Model trees. phpcbf accepts
    # explicit paths and auto-detects the repository
    # ruleset, so it runs directly on the files that
    # generation touched.
    return [
        "vendor/bin/phpcbf",
        *changed_paths,
    ]


def format_generated_code(repo, project, changed_paths=None):
    """Format freshly generated code the way generation CI does.

    When the changed paths are known and the project
    supports it, formatting is limited to those paths.
    PHP tolerates a failing formatter (generation CI runs
    `composer run fmt || true`); other projects treat a
    formatter failure as fatal for the service.
    """

    if not has_format_action(repo):
        return True

    commands = FORMAT_COMMANDS[project]

    if changed_paths:
        scoped = scoped_format_command(
            project,
            changed_paths,
        )

        if scoped is not None:
            commands = [scoped]

    for command in commands:
        formatting = run_command(command, repo)

        if formatting.returncode == 0:
            continue

        # The PHP formatting action deliberately uses
        # `composer run fmt || true`.
        if project == "php":
            print(
                "PHP formatter returned a non-zero exit code; "
                "continuing to match generation CI."
            )
            print(formatting.stdout[-3000:])
            continue

        print(
            f"Could not format "
            f"{PROJECT_LABELS[project]} generated code"
        )
        print(formatting.stdout[-3000:])
        return False

    return True


def load_services(root=ROOT):
    """Load the complete service catalog from services.json.

    The catalog file is the single source of truth for
    which services exist and which SDK projects generate
    them.
    """

    return checker.load_catalog(root / "config/services.json")


def select_services(all_services, requested_value):
    """Pick the services requested on the command line.

    Without a --services value every catalogued service
    is selected. Unknown names raise a ValueError, which
    main turns into a command line error.
    """

    if not requested_value:
        return all_services

    requested_ids = {
        value.strip().lower()
        for value in requested_value.split(",")
        if value.strip()
    }

    known_ids = {
        service["name"].lower()
        for service in all_services
    }

    unknown_ids = requested_ids - known_ids

    if unknown_ids:
        raise ValueError(
            "Unknown services: "
            + ", ".join(sorted(unknown_ids))
        )

    return [
        service
        for service in all_services
        if service["name"].lower() in requested_ids
    ]


def supports_project(service, project):
    """Return whether the catalog and language generator support a service.

    A service either whitelists projects explicitly or
    applies everywhere except its excludedProjects.
    Python and Ruby generators also skip webhook services.
    """

    if service["name"].endswith("Webhooks") and project in {"python", "ruby"}:
        return False

    allowed_projects = service.get("projects")
    excluded_projects = service.get(
        "excludedProjects",
        [],
    )

    if (
            allowed_projects is not None
            and project not in allowed_projects
    ):
        return False

    if project in excluded_projects:
        return False

    return True


def get_spec_name(service):
    """Return the OpenAPI family a catalogued service uses.

    The spec field overrides the default <name>Service
    convention for services whose spec file is named
    differently.
    """

    return service.get(
        "spec",
        f"{service['name']}Service",
    )


def lower_camel(value):
    """Lowercase only the first character of a name.

    SDK file names usually start lower (checkoutApi.ts)
    while catalog names start upper (Checkout).
    """

    if not value:
        return value

    return value[0].lower() + value[1:]


def discover_openapi_families(schema_directory):
    """Map every OpenAPI family to its newest version.

    Spec files follow the <Family>-v<Version>.json
    convention; when a family ships several versions,
    the highest one is kept.
    """

    return {
        family: max(versions)
        for family, versions in checker.discover_specs(
            schema_directory, public_only=True
        ).items()
    }


def audit_catalog(all_services, openapi_families, schema_directory):
    """Compare the service catalog with the OpenAPI repository.

    Produces three review lists: OpenAPI families the
    catalog never mentions, catalogued services pinned to
    an older version than OpenAPI currently publishes,
    and catalog entries whose expected spec file is
    missing entirely.
    """

    catalog_by_spec = {
        get_spec_name(service): service
        for service in all_services
    }

    uncatalogued = sorted(
        [
            (family_name, version)
            for family_name, version
            in openapi_families.items()
            if family_name not in catalog_by_spec
        ],
        key=lambda item: item[0],
    )

    catalog_versions_behind = sorted(
        [
            (
                service,
                openapi_families[
                    get_spec_name(service)
                ],
            )
            for service in all_services
            if (
                get_spec_name(service)
                in openapi_families
                and openapi_families[
                    get_spec_name(service)
                ]
                > service["version"]
        )
        ],
        key=lambda item: item[0]["name"],
    )

    missing_specifications = sorted(
        [
            service
            for service in all_services
            if (
                not (
                    schema_directory
                    / f"{get_spec_name(service)}-v{service['version']}.json"
                ).is_file()
        )
        ],
        key=lambda service: service["name"],
    )

    return (
        uncatalogued,
        catalog_versions_behind,
        missing_specifications,
    )


def load_family_titles(
        schema_directory,
        openapi_families,
):
    """Read the info.title of every OpenAPI family.

    Titles drive the generated-code search: files
    generated from a spec embed its title in their
    headers. Families whose spec cannot be read are left
    without a title.
    """

    titles = {}

    for (
            family_name,
            version,
    ) in openapi_families.items():
        spec_path = (
                schema_directory
                / f"{family_name}-v{version}.json"
        )

        try:
            spec = json.loads(
                spec_path.read_text(
                    encoding="utf-8"
                )
            )
        except (OSError, json.JSONDecodeError):
            continue

        title = spec.get("info", {}).get("title")

        if title:
            titles[family_name] = title

    return titles


def find_duplicate_families(
        schema_directory,
        uncatalogued,
):
    """Find uncatalogued families with identical API surfaces.

    Two specs exposing the same paths and schemas are
    almost certainly one API published twice, so both are
    reported as duplicates of each other. Servers and
    info metadata are ignored; only the API surface is
    compared.
    """

    digests = {}

    for family_name, version in uncatalogued:
        spec_path = (
                schema_directory
                / f"{family_name}-v{version}.json"
        )

        try:
            spec = json.loads(
                spec_path.read_text(
                    encoding="utf-8"
                )
            )
        except (OSError, json.JSONDecodeError):
            continue

        # Compare API surfaces only; servers and info
        # metadata can differ between identical specs.
        surface = {
            key: spec.get(key)
            for key in ("paths", "components")
        }

        digests[family_name] = hashlib.sha256(
            json.dumps(
                surface,
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()

    families_by_digest = {}

    for family_name, digest in digests.items():
        families_by_digest.setdefault(
            digest,
            [],
        ).append(family_name)

    duplicates = {}

    for members in families_by_digest.values():
        if len(members) < 2:
            continue

        for family_name in members:
            duplicates[family_name] = ", ".join(
                sorted(
                    member
                    for member in members
                    if member != family_name
                )
            )

    return duplicates


def title_search_needles(title):
    """Return searchable forms of a spec title.

    Generated files embed the spec title, but titles can
    carry trailing parentheticals ("(deprecated)") that
    generated headers drop, so both forms are searched.
    """

    needles = [title]

    without_parenthetical = re.sub(
        r"\s*\([^()]*\)\s*$",
        "",
        title,
    ).strip()

    if (
            without_parenthetical
            and without_parenthetical != title
    ):
        needles.append(without_parenthetical)

    return needles


def searchable_title_needles(title):
    """Return title needles that are specific enough.

    Single-word titles such as "Webhooks" appear in
    almost every SDK for unrelated reasons, so families
    with only generic words cannot be searched by title.
    """

    # Single-word titles ("Webhooks") match unrelated
    # code in almost every SDK.
    return [
        needle
        for needle in title_search_needles(title)
        if " " in needle
    ]


def family_candidate_names(family_name, project):
    """Return every name an SDK might use for a family.

    The list contains the family itself, the family
    without its Service suffix, the historical aliases
    from FAMILY_ALIASES, and the per-project aliases from
    FAMILY_PROJECT_ALIASES.
    """

    names = [family_name]

    if family_name.endswith("Service"):
        names.append(
            family_name.removesuffix("Service")
        )

    names.extend(
        FAMILY_ALIASES.get(family_name, [])
    )

    names.extend(
        FAMILY_PROJECT_ALIASES
        .get(family_name, {})
        .get(project, [])
    )

    return names


def resolve_existing_path(path):
    """Return the existing sibling of a path, ignoring casing.

    SDK repositories are inconsistent about file-name
    casing (marketpay.rb vs marketPay.rb), so a miss on
    the exact name falls back to a case-insensitive
    lookup inside the parent directory.
    """

    if path.exists():
        return path

    parent = path.parent

    if not parent.is_dir():
        return None

    wanted = path.name.lower()

    for candidate in parent.iterdir():
        if candidate.name.lower() == wanted:
            return candidate

    return None


def clean_temporary_sdk(repo):
    """Reset an SDK clone to its committed state.

    Generation runs once per service, so the repository
    must be pristine before every run; leftovers from the
    previous service would pollute the next diff.
    """

    if not repo.exists():
        return True

    commands = [
        ["git", "reset", "--hard", "HEAD"],
        ["git", "clean", "-fd"],
    ]

    for command in commands:
        result = run_command(command, repo)

        if result.returncode != 0:
            print(result.stdout)
            return False

    return True


def read_service_version_from_log(repo, service):
    """Read the version recorded in the SDK's generation log.

    The SDK repositories commit sdk-generation-log/
    <service>.json, and its specVersion states which spec
    version the committed code was generated from.
    """

    service_id = service["name"].lower()

    log_path = (
            repo
            / "sdk-generation-log"
            / f"{service_id}.json"
    )

    if not log_path.exists():
        return None

    try:
        log_data = json.loads(
            log_path.read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError):
        return None

    spec_version = log_data.get("specVersion")

    if (
            isinstance(spec_version, int)
            and not isinstance(spec_version, bool)
    ):
        return spec_version

    return None


def service_source_paths(repo, project, service):
    """Return the exact source locations a service owns.

    These are the paths the generator writes to in each
    language, including the few naming quirks such as
    Go's payments package and .NET's PascalCase folders.
    """

    name = service["name"]
    service_id = name.lower()
    camel_name = lower_camel(name)

    if project == "java":
        return [
            (
                    repo
                    / "src/main/java/com/adyen/model"
                    / service_id
            ),
            (
                    repo
                    / "src/main/java/com/adyen/service"
                    / service_id
            ),
        ]

    if project == "node":
        return [
            repo / "src/typings" / camel_name,
            repo / "src/services" / camel_name,
            repo / "src/services" / f"{camel_name}Api.ts",
            ]

    if project == "python":
        python_names = {
            "BinLookup": "binlookup",
            "Payment": "payments",
            "Payout": "payouts",
            "PosTerminalManagement": "terminal",
        }

        python_name = python_names.get(
            name,
            camel_name,
        )

        return [
            repo / "Adyen/services" / python_name,
            repo / "Adyen/services" / f"{python_name}.py",
            ]

    if project == "php":
        php_names = {
            "Payment": "Payments",
        }

        php_name = php_names.get(name, name)

        return [
            repo / "src/Adyen/Model" / php_name,
            repo / "src/Adyen/Service" / php_name,
            (
                    repo
                    / "src/Adyen/Service"
                    / f"{php_name}Api.php"
            ),
            ]

    if project == "ruby":
        return [
            repo / "lib/adyen/services" / camel_name,
            (
                    repo
                    / "lib/adyen/services"
                    / f"{camel_name}.rb"
            ),
            ]

    if project == "go":
        go_name = service_id

        if name == "Payment":
            go_name = "payments"
        elif name == "LegalEntityManagement":
            go_name = "legalentity"
        elif name.endswith("Webhooks"):
            go_name = service_id.removesuffix("s")

        return [
            repo / "src" / go_name,
            ]

    if project == "dotnet":
        return [
            repo / "Adyen" / name,
            ]

    return []


def read_version_from_source_paths(paths, project):
    """Read a service version from its source files.

    The language's version marker is searched inside the
    given paths only. A version is reported when every
    marker in every file agrees; anything less certain
    stays unknown rather than guessed.
    """

    discovered_versions = set()
    version_pattern = VERSION_PATTERNS.get(project)

    if version_pattern is None:
        return None

    for source_path in paths:
        if not source_path.exists():
            continue

        if source_path.is_file():
            source_files = [source_path]
        else:
            source_files = [
                path
                for path in source_path.rglob("*")
                if path.is_file()
            ]

        for source_file in source_files:
            if (
                    source_file.suffix.lower()
                    not in SOURCE_EXTENSIONS
            ):
                continue

            try:
                content = source_file.read_text(
                    encoding="utf-8",
                    errors="ignore",
                )
            except OSError:
                continue

            for match in version_pattern.finditer(
                    content
            ):
                discovered_versions.add(
                    int(match.group(1))
                )

    # Trust the source only when every marker agrees.
    if len(discovered_versions) == 1:
        return discovered_versions.pop()

    return None


def family_source_paths(repo, project, names):
    """Return candidate source locations for family names.

    Combines the generator's output locations with the
    hand-written locations that predate generation, such
    as PHP's single-file Service/Fund.php services.
    """

    paths = []

    for name in names:
        # Exact generation locations of a catalogued
        # service with this name.
        paths.extend(
            service_source_paths(
                repo,
                project,
                {"name": name},
            )
        )

        camel_name = lower_camel(name)

        # Locations of hand-written, single-file services
        # that predate generation.
        if project == "java":
            paths.append(
                    repo
                    / "src/main/java"
                    / "com/adyen/service"
                    / f"{name}Api.java"
            )
        elif project == "node":
            paths.append(
                    repo
                    / "src/typings"
                    / f"{camel_name}.ts"
            )
        elif project == "python":
            paths.append(
                    repo
                    / "Adyen/services"
                    / f"{camel_name}.py"
            )
        elif project == "php":
            paths.append(
                    repo
                    / "src/Adyen/Service"
                    / f"{name}.php"
            )

    return paths


def find_family_paths(repo, project, family_name):
    """Return the source paths an SDK really has for a family.

    Every candidate name resolves against the file system
    (case-insensitively); the paths that exist are the
    evidence that the SDK ships the family.
    """

    names = family_candidate_names(
        family_name,
        project,
    )

    existing = []

    for path in family_source_paths(
            repo,
            project,
            names,
    ):
        resolved = resolve_existing_path(path)

        if resolved is None:
            continue

        if resolved not in existing:
            existing.append(resolved)

    return existing


def family_title_patterns(title):
    """Match a specific API title on its own header line, not inside prose."""
    return [
        (
            needle,
            re.compile(
                r"^[ \t]*(?:[#*/]+[ \t]*)?"
                + re.escape(needle)
                + r"[ \t]*$",
                re.MULTILINE,
            ),
        )
        for needle in searchable_title_needles(title)
    ]


def scan_family_titles(
        repo,
        project,
        families,
        titles,
):
    """Detect generated family code through spec titles.

    A family is only reported when a file shows the spec
    title on its own line together with a version marker;
    plain mentions inside descriptions are ignored, since
    generated file headers put the title on its own line
    while hand-written code only mentions it in prose.
    """

    version_pattern = VERSION_PATTERNS.get(project)

    if version_pattern is None:
        return {}

    searched = {}

    for family_name in families:
        needles = searchable_title_needles(
            titles[family_name]
        )

        if not needles:
            continue

        searched[family_name] = family_title_patterns(titles[family_name])

    if not searched:
        return {}

    detected = {}

    for source_file in repo.rglob("*"):
        if (
                not source_file.is_file()
                or source_file.suffix.lower()
                not in SOURCE_EXTENSIONS
        ):
            continue

        try:
            content = source_file.read_text(
                encoding="utf-8",
                errors="ignore",
            )
        except OSError:
            continue

        for (
                family_name,
                needles,
        ) in searched.items():
            # Cheap substring check before the line
            # pattern runs.
            if not any(
                    needle in content
                    for needle, _ in needles
            ):
                continue

            if not any(
                    pattern.search(content)
                    for _, pattern in needles
            ):
                continue

            # The same file must carry a version marker.
            file_versions = {
                int(match.group(1))
                for match
                in version_pattern.finditer(
                    content
                )
            }

            if not file_versions:
                continue

            detected.setdefault(
                family_name,
                set(),
            ).update(file_versions)

    return {
        family_name: (
            versions.pop()
            if len(versions) == 1
            else None
        )
        for family_name, versions
        in detected.items()
    }


def detect_sdk_families(
        repo,
        project,
        uncatalogued,
        titles,
):
    """Report which uncatalogued families an SDK ships.

    Two signals count as presence: files at known service
    locations, and generated files carrying the spec
    title. A version is only reported when both signals
    agree on one number, and families with hopelessly
    generic names stay Unknown.
    """

    searchable = [
        family_name
        for family_name in uncatalogued
        if searchable_title_needles(
            titles.get(family_name, "")
        )
    ]

    title_versions = scan_family_titles(
        repo,
        project,
        searchable,
        {
            family_name: titles[family_name]
            for family_name in searchable
        },
    )

    findings = {}

    for family_name in uncatalogued:
        if family_name not in searchable:
            # Generic names cannot be searched reliably.
            findings[family_name] = (
                "Unknown",
                None,
            )

            continue

        present = False
        versions = set()
        uncertain_version = False

        path_hits = find_family_paths(
            repo,
            project,
            family_name,
        )

        if path_hits:
            present = True

            path_version = (
                read_version_from_source_paths(
                    path_hits,
                    project,
                )
            )

            if path_version is not None:
                versions.add(path_version)
            else:
                uncertain_version = True

        if family_name in title_versions:
            present = True

            title_version = title_versions[
                family_name
            ]

            if title_version is not None:
                versions.add(title_version)
            else:
                uncertain_version = True

        version = (
            versions.pop()
            if len(versions) == 1 and not uncertain_version
            else None
        )

        findings[family_name] = (
            "Present" if present else "Absent",
            version,
        )

    return findings


def format_family_sdk_summary(
        family_findings,
        family_name,
):
    """Build the "Already in SDK" cell for the audit table.

    Lists the projects that ship the family with the
    version when it is known, "None" when no SDK ships
    it, and "Not assessed" when the family name is too
    generic to search for.
    """

    summaries = []
    assessed = False

    for project in PROJECTS:
        findings = family_findings.get(project)

        if findings is None:
            continue

        state, version = findings[family_name]

        if state == "Unknown":
            continue

        assessed = True

        if state != "Present":
            continue

        label = PROJECT_LABELS[project]

        if version is not None:
            summaries.append(
                f"{label} (v{version})"
            )
        else:
            summaries.append(label)

    if summaries:
        return ", ".join(summaries)

    if assessed:
        return "None"

    return "Not assessed"


def read_service_version(
        repo,
        project,
        service,
):
    """Read the version of a service inside an SDK.

    The committed generation log is trusted first, and
    version markers in the source files are the fallback.
    A None result means the version could not be read,
    which the report shows as "Behind".
    """

    # The generation log is the preferred source.
    log_version = read_service_version_from_log(
        repo,
        service,
    )

    if log_version is not None:
        return log_version

    # Generated source is a fallback.
    paths = service_source_paths(
        repo,
        project,
        service,
    )

    return read_version_from_source_paths(
        paths,
        project,
    )


def read_committed_sdk_sources(repo, project):
    """Read production source and generation logs from one immutable SDK commit."""
    head = run_command(["git", "rev-parse", "--verify", "HEAD^{commit}"], repo)
    if head.returncode != 0:
        raise OSError("Could not identify the committed SDK snapshot")
    commit = head.stdout.strip()
    if not re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", commit):
        raise OSError("Invalid committed SDK snapshot")
    source_root, source_extension = SOURCE_ROOTS[project]
    tree = run_command(
        ["git", "ls-tree", "-r", "-z", commit, "--", source_root, "sdk-generation-log"],
        repo,
    )
    if tree.returncode != 0:
        raise OSError("Could not list committed SDK source")
    entries = []
    for record in tree.stdout.split("\0"):
        if not record:
            continue
        metadata, name = record.split("\t", 1)
        mode, kind, blob = metadata.split()
        path = Path(name)
        if mode not in {"100644", "100755"} or kind != "blob":
            continue
        if {"test", "tests", "__tests__"} & {part.lower() for part in path.parts}:
            continue
        if name.endswith(("_test.go", ".test.ts", ".spec.ts", "Test.java", "Tests.cs")):
            continue
        if path.suffix.lower() == source_extension or (
            path.parent == Path("sdk-generation-log") and path.suffix == ".json"
        ):
            entries.append((name, blob))
    entries.sort()
    if not entries:
        return commit, {}
    blobs = subprocess.run(
        ["git", "cat-file", "--batch"],
        cwd=repo,
        input="".join(f"{blob}\n" for _, blob in entries).encode(),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if blobs.returncode != 0:
        raise OSError("Could not read committed SDK source")
    sources = {}
    offset = 0
    for name, blob in entries:
        end = blobs.stdout.index(b"\n", offset)
        actual_blob, kind, size = blobs.stdout[offset:end].split()
        if actual_blob.decode() != blob or kind != b"blob":
            raise OSError(f"Could not read committed SDK file: {name}")
        offset = end + 1
        size = int(size)
        sources[name] = blobs.stdout[offset:offset + size].decode("utf-8")
        offset += size + 1
    return commit, sources


def detect_unsupported_services(repo, project, services, titles):
    """Check source presence without claiming that unsupported code was regenerated."""
    commit, sources = read_committed_sdk_sources(repo, project)
    results = {}
    for service in services:
        name = service["name"]
        family = get_spec_name(service)
        title = titles.get(family, "")
        needles = set(searchable_title_needles(title))
        title_patterns = family_title_patterns(title)
        shared_title = any(
            other != family and needles.intersection(searchable_title_needles(other_title))
            for other, other_title in titles.items()
        )
        paths = [path.relative_to(repo).as_posix().lower()
                 for path in service_source_paths(repo, project, service)]
        identities = {
            identity.replace("_", "").lower()
            for base in (name, family.removesuffix("Service"))
            for identity in (base, base + "Api", "Adyen" + base + "Api")
        }
        versions = set()
        matches = []
        ambiguous = False
        log_evidence = None
        for path, content in sorted(sources.items()):
            if Path(path).suffix.lower() not in SOURCE_EXTENSIONS:
                continue
            declarations = list(SOURCE_DECLARATION.finditer(content))
            owned = any(path.lower() == folder or path.lower().startswith(folder + "/") for folder in paths)
            declaration = next((
                match for match in declarations
                if match.group(1).replace("_", "").lower() in identities
            ), None)
            header_text = content[:declarations[0].start()] if declarations else ""
            header = next((
                match for _, pattern in title_patterns
                if (match := pattern.search(header_text))
            ), None)
            generated = header is not None and "OpenAPI Generator" in header_text
            if not (owned and declaration) and not (generated and not shared_title):
                ambiguous = ambiguous or owned or (generated and shared_title)
                continue
            evidence = declaration if owned and declaration else header
            rule = "known service path and declaration" if owned and declaration else "generated API title"
            line = content[:evidence.start()].count("\n") + 1
            file_versions = {
                int(match.group(1))
                for pattern in (VERSION_PATTERNS[project], VERSION_PATTERNS["java"])
                for match in pattern.finditer(content)
                if int(match.group(1)) > 0
            }
            versions.update(file_versions)
            matches.append((path, line, rule, sorted(file_versions)))
        if matches:
            log_path = f"sdk-generation-log/{name.lower()}.json"
            log = sources.get(log_path)
            if log is not None:
                log_version = json.loads(log).get("specVersion")
                if type(log_version) is int and log_version > 0:
                    versions.add(log_version)
                    log_evidence = f"  {log_path}: specVersion {log_version}"
            status = "Unsupported; in SDK"
            if len(versions) == 1 and not ambiguous:
                status += f" at v{next(iter(versions))}"
        else:
            status = UNSUPPORTED_NOT_ASSESSED if ambiguous else "Unsupported"
        results[name.lower()] = status
        print(f"{PROJECT_LABELS[project]} {name}: {status} (SDK commit {commit})")
        for path, line, rule, file_versions in matches:
            print(f"  {path}:{line}: {rule}; source versions {file_versions or 'unknown'}")
        if log_evidence:
            print(log_evidence)
    return results


def check_service(workspace, project, service):
    """Generate one service and classify the result.

    The SDK is reset, its current version is read, the
    service is generated, the output is formatted, and
    the final git state becomes the classification: an
    unchanged repo means Current, a changed service at
    the target version is drift, an older service is
    behind, and a changed service of unknown version is
    Behind.
    """

    service_name = service["name"]
    if not supports_project(service, project):
        return UNSUPPORTED_NOT_ASSESSED
    spec_file = workspace / "schema/json" / f"{get_spec_name(service)}-v{service['version']}.json"
    if not spec_file.is_file():
        print(f"Warning: missing {spec_file.name}; skipping {service_name} generation.")
        return "Missing spec"
    service_id = service_name.lower()
    target_version = service["version"]

    project_label = PROJECT_LABELS[project]
    repo = workspace / project / "repo"

    print(
        f"Checking {project_label} "
        f"{service_name}..."
    )

    if not clean_temporary_sdk(repo):
        return "Failed"

    # Read the clean SDK before generation.
    sdk_service_version = read_service_version(
        repo,
        project,
        service,
    )

    generation = run_command(
        [
            str(workspace / "gradlew"),
            f":{project}:{service_id}",
        ],
        workspace,
    )

    if generation.returncode != 0:
        print(
            f"{project_label} "
            f"{service_name}: Failed"
        )
        print(generation.stdout[-3000:])
        return "Failed"

    # Collect what generation changed so the formatter can
    # skip the rest of the library. An empty result means
    # nothing changed, so formatting is skipped entirely;
    # an unknown result falls back to the full command.
    changed_paths = changed_repo_paths(repo)

    if changed_paths is None or changed_paths:
        if not format_generated_code(
                repo,
                project,
                changed_paths,
        ):
            return "Failed"

    status = run_command(
        [
            "git",
            "status",
            "--short",
        ],
        repo,
    )

    if status.returncode != 0:
        print(
            f"Could not inspect "
            f"{project_label} {service_name}"
        )
        return "Failed"

    has_changes = bool(status.stdout.strip())

    if not has_changes:
        source_paths = service_source_paths(repo, project, service)
        has_source = any(
            path.is_file() and path.suffix in SOURCE_EXTENSIONS
            or path.is_dir() and any(
                child.is_file() and child.suffix in SOURCE_EXTENSIONS
                for child in path.rglob("*")
            )
            for path in source_paths
        )
        if not has_source or sdk_service_version not in {None, target_version}:
            result = "Not assessed"
        else:
            result = f"Current v{target_version}"

    elif (
            sdk_service_version is not None
            and sdk_service_version < target_version
    ):
        result = (
            "Service version behind "
            f"v{sdk_service_version}"
        )

    elif sdk_service_version == target_version:
        result = (
            f"Service drift at v{target_version}"
        )

    else:
        result = "Behind"

    print(
        f"{project_label} "
        f"{service_name}: {result}"
    )

    return result


NO_BASELINE_ENTRY = "No baseline entry"


def pinned_entry(pinned_entries, service, latest_version):
    """Return the version pin that acknowledges the latest version.

    A pin recorded for an older release no longer applies, matching
    how the spec coverage check accepts pins.
    """

    entry = pinned_entries.get(get_spec_name(service))

    if entry is None or entry.get("acknowledgedVersion") != latest_version:
        return None

    return entry


def baseline_reason(entry):
    """Return the recorded baseline reason for one report cell.

    Only reviewed text is copied into the report. UNREVIEWED
    placeholders render as empty cells; absent entries keep
    their fixed label.
    """

    if entry is None:
        return NO_BASELINE_ENTRY

    reason = str(entry.get("reason", "")).strip()

    if not reason or reason.upper().startswith("UNREVIEWED:"):
        return ""

    return " ".join(reason.split()).replace("|", "\\|")


def build_audit_lines(
        uncatalogued,
        catalog_versions_behind,
        missing_specifications,
        family_findings,
        duplicate_families,
        baseline=None,
):
    """Build the OpenAPI catalog audit section.

    Three findings follow a fixed review order: services
    catalogued against an outdated spec version, OpenAPI
    families the catalog never mentions (with the SDKs
    that already ship them), and catalog entries whose
    spec file is missing from OpenAPI.
    """

    baseline = baseline or {"uncoveredSpecs": {}, "pinnedVersions": {}}
    uncovered_entries = baseline["uncoveredSpecs"]
    pinned_entries = baseline["pinnedVersions"]

    lines = [
        "## OpenAPI catalog audit",
        "",
        "All catalog differences are shown, including gaps recorded in the spec coverage baseline.",
        "",
    ]

    if catalog_versions_behind:
        lines.extend(
            [
                "### Catalog versions behind OpenAPI",
                "",
                "| Catalog service | OpenAPI family | Catalog version | Latest OpenAPI version | Baseline reason |",
                "|---|---|---:|---:|---|",
            ]
        )

        for (
                service,
                latest_version,
        ) in catalog_versions_behind:
            lines.append(
                f"| {service['name']} | "
                f"{get_spec_name(service)} | "
                f"{service['version']} | "
                f"{latest_version} | "
                f"{baseline_reason(pinned_entry(pinned_entries, service, latest_version))} |"
            )

        lines.append("")
    else:
        lines.extend(
            [
                "No catalog service uses an older OpenAPI version.",
                "",
            ]
        )

    if uncatalogued:
        lines.extend(
            [
                "### OpenAPI families not catalogued",
                "",
                "| OpenAPI family | Latest version | Already in SDK | Baseline reason |",
                "|---|---:|---|---|",
            ]
        )

        for family_name, version in uncatalogued:
            summary = format_family_sdk_summary(
                family_findings,
                family_name,
            )

            lines.append(
                f"| {family_name} | {version} "
                f"| {summary} "
                f"| {baseline_reason(uncovered_entries.get(family_name))} |"
            )

        lines.append("")

        for family_name, twins in sorted(
                duplicate_families.items()
        ):
            lines.append(
                f"- {family_name} has an API surface "
                f"identical to {twins}."
            )

        if duplicate_families:
            lines.append("")
    else:
        lines.extend(
            [
                "Every OpenAPI family is represented in the catalog.",
                "",
            ]
        )

    if missing_specifications:
        lines.extend(
            [
                "### Catalog entries without an OpenAPI file",
                "",
                "| Catalog service | Expected OpenAPI family | Version |",
                "|---|---|---:|",
            ]
        )

        for service in missing_specifications:
            lines.append(
                f"| {service['name']} | "
                f"{get_spec_name(service)} | "
                f"{service['version']} |"
            )

        lines.append("")

    return lines


def build_report(
        selected_services,
        results,
        uncatalogued,
        catalog_versions_behind,
        missing_specifications,
        family_findings,
        duplicate_families,
        baseline=None,
):
    """Assemble the complete Markdown report.

    The report has three parts: a timestamped header, the catalog
    audit with its findings, and the generation coverage
    table with one row per service and per uncatalogued
    family, followed by the legend.
    """

    generated_at = datetime.now(
        timezone.utc
    ).isoformat(timespec="seconds")

    headers = [
        "Service",
        "Target version",
        *[
            PROJECT_LABELS[project]
            for project in PROJECTS
        ],
    ]

    header_row = (
            "| " + " | ".join(headers) + " |"
    )

    separator_row = (
            "|---|---:|"
            + "|".join("---" for _ in PROJECTS)
            + "|"
    )

    rows = []

    for service in selected_services:
        service_id = service["name"].lower()

        cells = [
            service["name"],
            f"v{service['version']}",
        ]

        for project in PROJECTS:
            cells.append(
                results[(project, service_id)]
            )

        rows.append(
            "| " + " | ".join(cells) + " |"
        )

    for family_name, version in uncatalogued:
        cells = [
            family_name,
            f"v{version}",
        ]

        for project in PROJECTS:
            findings = family_findings.get(project)

            if findings is None:
                cells.append("Failed")

                continue

            state, sdk_version = findings[
                family_name
            ]

            if state == "Present":
                if sdk_version is not None:
                    cells.append(
                        f"In SDK at v{sdk_version}"
                    )
                else:
                    cells.append("In SDK")
            elif state == "Absent":
                cells.append("Not catalogued")
            else:
                # Generic names cannot be assessed.
                cells.append("Not assessed")

        rows.append(
            "| " + " | ".join(cells) + " |"
        )

    report_lines = [
        "# SDK coverage",
        "",
        f"Generated at: `{generated_at}`",
        "",
    ]

    report_lines.extend(
        build_audit_lines(
            uncatalogued,
            catalog_versions_behind,
            missing_specifications,
            family_findings,
            duplicate_families,
            baseline,
        )
    )

    report_lines.extend(
        [
            "## SDK generation coverage",
            "",
            header_row,
            separator_row,
            *rows,
            "",
            "Notes:",
            "",
            "- Checks use the OpenAPI versions pinned in the generation catalog, "
            "not necessarily the latest available versions. See the catalog audit "
            "for newer OpenAPI versions.",
            "- `Current vN`: the SDK is up to date with the catalogued OpenAPI "
            "service at version N; regenerating it produces no changes.",
            "- `Service version behind vX`: the SDK uses service version X, "
            "which is older than the catalogued OpenAPI version.",
            "- `Service drift at vN`: the SDK and the catalogued OpenAPI service "
            "use version N, but regenerating the SDK produces changes. The SDK "
            "may be missing recent spec changes, or the differences may come "
            "from generator or template changes.",
            "- `Behind`: the SDK differs from the generated OpenAPI code, "
            "but we cannot reliably compare service versions; "
            "check the SDK version manually.",
            "- `Failed`: the report could not complete this SDK/service check "
            "because setup, generation, formatting, or inspection failed. "
            "See the run log; this does not by itself mean the SDK is behind.",
            "- `Missing spec`: the catalog references an OpenAPI file that "
            "is missing. Generation was skipped for this service "
            "(warning only).",
            "- `Unsupported`: this service is not enabled for this SDK in "
            "the catalog or language generator. This describes generation "
            "support, not whether the SDK contains the service.",
            "- `Unsupported; in SDK at vN`: generation is not supported, "
            "but family-specific source and one consistent version were found.",
            "- `Unsupported; in SDK`: family-specific source was found, "
            "but its version is missing or conflicting.",
            "- `Unsupported; presence not assessed`: source could not be "
            "inspected or the evidence was ambiguous.",
            "- Unsupported-service presence checks read committed production "
            "source before generation. They require a known service path with "
            "a matching declaration, or an exact, unique generated API title. "
            "Generic webhook/HMAC helpers do not establish family presence. "
            "Evidence paths and the SDK commit are printed in the run log. "
            "Presence does not prove complete webhook support.",
            "- Uncatalogued families: these OpenAPI families are not in the "
            "generation catalog. They appear in the audit and coverage table, "
            "and may already be present in SDKs.",
            "- `In SDK at vN`: the SDK already ships this OpenAPI family at "
            "version N, but it is not in the generation catalog.",
            "- `In SDK`: the SDK already ships this OpenAPI family, but its "
            "version could not be detected and it is not in the generation catalog.",
            "- `Not catalogued`: this OpenAPI family is missing from the "
            "generation catalog, and no matching code was found in this SDK.",
            "- `Not assessed`: the report could not confirm whether this "
            "SDK includes the OpenAPI family or matches the target version. "
            "Check manually; this does not mean unsupported or absent.",
            "- Baseline reason: copied word for word from "
            "`config/spec-coverage-baseline.json`. It explains a recorded "
            "gap and does not change any status.",
            "- Empty baseline reason cells: the baseline entry has no "
            "reviewed reason, so no reason is shown.",
            f"- `{NO_BASELINE_ENTRY}`: the family is not listed in the baseline. "
            "For catalog versions behind OpenAPI, no version pin "
            "acknowledges the latest OpenAPI version.",
            "- Uncatalogued detection relies on spec titles, version markers,",
            "  and standard service locations; hand-written code under",
            "  unusual names may not be detected.",
            "- Presence labels report that the SDK ships the family; they do",
            "  not distinguish spec-generated code from hand-written legacy",
            "  code.",
            "- Ruby uses hashes instead of generated models, so its result covers services only.",
            "",
        ]
    )

    return "\n".join(report_lines)


def clone_automation_repo(destination):
    """Clone this repository into a workspace.

    A local clone gives every workspace an isolated copy
    of the Gradle build, independent of the checkout the
    script itself runs from.
    """

    clone = run_command(
        [
            "git",
            "clone",
            "--local",
            "--no-hardlinks",
            str(ROOT),
            str(destination),
        ],
        ROOT,
    )

    if clone.returncode != 0:
        print(clone.stdout[-3000:])

        return False

    return True


def prepare_project_workspace(
        temp,
        shared_schema,
        project,
):
    """Create an isolated workspace for one project.

    Concurrent Gradle builds contend on file locks inside
    a shared workspace, so every project gets its own copy
    of the automation repository and of the OpenAPI
    specifications.
    """

    workspace = temp / f"automation-{project}"

    if not clone_automation_repo(workspace):
        return None

    # The specifications are copied rather than cloned:
    # the specs task processes them in place after
    # cloning, and a git clone would lose that work.
    try:
        # Match the per-language generator dependency selected by generation CI.
        shutil.copyfile(
            workspace / project / "gradle.properties",
            workspace / "buildSrc/gradle.properties",
        )
        shutil.copytree(
            shared_schema,
            workspace / "schema",
        )
    except OSError as error:
        print(
            f"Could not prepare the workspace for "
            f"{PROJECT_LABELS[project]}: {error}"
        )

        return None

    return workspace


def run_project(
        temp,
        shared_schema,
        project,
        selected_services,
        uncatalogued_families,
        family_titles,
):
    """Check one project inside its own workspace.

    Clones the automation repository, fetches the SDK,
    scans it for uncatalogued families while it is still
    clean, and generates every applicable service. Any
    failure along the way marks the remaining services
    Failed or Unsupported so the report always has a
    complete row. The fourth return value records worker
    failures independently of warning-only service results.
    """

    project_label = PROJECT_LABELS[project]
    service_results = {}
    findings = None
    project_failed = False
    unsupported_services = []

    # Keep missing-input warnings separate from build/formatter failures.
    for service in selected_services:
        service_id = service["name"].lower()
        spec_file = shared_schema / "json" / f"{get_spec_name(service)}-v{service['version']}.json"
        if not supports_project(service, project):
            service_results[service_id] = UNSUPPORTED_NOT_ASSESSED
            unsupported_services.append(service)
        elif not spec_file.is_file():
            service_results[service_id] = "Missing spec"

    def mark_unavailable():
        """Record the worker failure without replacing warnings or unsupported rows."""

        nonlocal project_failed
        project_failed = True
        for service in selected_services:
            service_results.setdefault(service["name"].lower(), "Failed")

    print(
        f"Preparing {project_label} SDK..."
    )

    try:
        workspace = prepare_project_workspace(
            temp,
            shared_schema,
            project,
        )

        if workspace is None:
            mark_unavailable()

            return (
                project,
                service_results,
                findings,
                project_failed,
            )

        clone_sdk = run_command(
            [
                str(workspace / "gradlew"),
                f":{project}:cloneRepo",
            ],
            workspace,
        )

        if clone_sdk.returncode != 0:
            print(
                f"Could not clone "
                f"{project_label} SDK"
            )
            print(clone_sdk.stdout[-3000:])

            mark_unavailable()

            return (
                project,
                service_results,
                findings,
                project_failed,
            )

        repo = workspace / project / "repo"

        if unsupported_services:
            service_results.update(detect_unsupported_services(
                repo, project, unsupported_services, family_titles,
            ))

        print(
            f"Scanning {project_label} SDK "
            f"for uncatalogued families..."
        )

        # The SDK is still clean before any generation.
        findings = detect_sdk_families(
            repo,
            project,
            uncatalogued_families,
            family_titles,
        )

        if not prepare_formatter(repo, project):
            mark_unavailable()

            return (
                project,
                service_results,
                findings,
                project_failed,
            )

        for service in selected_services:
            service_id = (
                service["name"].lower()
            )

            if service_id in service_results:
                continue

            service_results[service_id] = check_service(
                workspace,
                project,
                service,
            )
    except Exception as error:
        print(
            f"Unexpected {project_label} "
            f"failure: {error!r}"
        )

        mark_unavailable()

    return (
        project,
        service_results,
        findings,
        project_failed,
    )


def main():
    """Run the full coverage check and write the report.

    Prepares the OpenAPI specifications once, runs every
    SDK project inside its own isolated workspace (in
    parallel by default), and assembles the results into
    sdk-coverage.md next to the repository root.
    """

    parser = argparse.ArgumentParser(
        description=(
            "Generate an SDK service coverage report."
        )
    )

    parser.add_argument(
        "--services",
        help=(
            "Comma-separated service IDs, "
            "for example: checkout,management"
        ),
    )

    parser.add_argument(
        "--jobs",
        type=int,
        default=len(PROJECTS),
        help=(
            "Number of SDK projects to check "
            "in parallel."
        ),
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "sdk-coverage.md",
        help="Write the Markdown report to this path.",
    )

    args = parser.parse_args()

    results = {}
    worker_failed = False
    family_findings = {}
    openapi_families = {}

    with tempfile.TemporaryDirectory(
            prefix="adyen-sdk-coverage-"
    ) as temp:
        workspace = Path(temp) / "automation"

        print(
            f"Temporary workspace: {workspace}"
        )

        if not clone_automation_repo(workspace):
            print(
                "Could not create temporary workspace"
            )
            return 1

        # Generation runs committed HEAD in isolated clones. Read that same
        # catalog and baseline, not uncommitted edits in the caller's working tree.
        try:
            all_services = load_services(workspace)
            baseline = checker.load_baseline(
                workspace / "config/spec-coverage-baseline.json"
            )
        except (OSError, ValueError, checker.BaselineError) as error:
            print(f"Could not read the service catalog or spec coverage baseline: {error}")
            return 1
        try:
            selected_services = select_services(all_services, args.services)
        except ValueError as error:
            parser.error(str(error))

        print(
            "Downloading OpenAPI specifications..."
        )

        specs = run_command(
            [
                str(workspace / "gradlew"),
                "specs",
            ],
            workspace,
        )

        if specs.returncode != 0:
            print(
                "Could not download OpenAPI specifications"
            )
            print(specs.stdout[-3000:])
            return 1

        schema_directory = (
                workspace / "schema/json"
        )

        openapi_families = (
            discover_openapi_families(
                schema_directory
            )
        )

        (
            uncatalogued,
            catalog_versions_behind,
            missing_specifications,
        ) = audit_catalog(
            all_services,
            openapi_families,
            schema_directory,
        )

        family_titles = load_family_titles(
            schema_directory,
            openapi_families,
        )

        duplicate_families = (
            find_duplicate_families(
                schema_directory,
                uncatalogued,
            )
        )

        # Every project runs inside its own workspace so
        # that Gradle builds never contend on file locks.
        workers = max(
            1,
            min(args.jobs, len(PROJECTS)),
        )

        print(
            f"Checking {len(PROJECTS)} SDK projects "
            f"with up to {workers} parallel job(s)..."
        )

        with ThreadPoolExecutor(
                max_workers=workers,
                thread_name_prefix="sdk-coverage",
        ) as pool:
            futures = [
                pool.submit(
                    run_project,
                    Path(temp),
                    schema_directory.parent,
                    project,
                    selected_services,
                    [
                        family_name
                        for family_name, _
                        in uncatalogued
                    ],
                    family_titles,
                )
                for project in PROJECTS
            ]

            for future in futures:
                (
                    project,
                    project_results,
                    project_findings,
                    project_failed,
                ) = future.result()
                worker_failed = worker_failed or project_failed

                for (
                        service_id,
                        result,
                ) in project_results.items():
                    results[
                        (project, service_id)
                    ] = result

                if project_findings is not None:
                    family_findings[project] = (
                        project_findings
                    )

    print("Temporary workspace deleted")

    report = build_report(
        selected_services,
        results,
        uncatalogued,
        catalog_versions_behind,
        missing_specifications,
        family_findings,
        duplicate_families,
        baseline,
    )

    report_path = args.output
    report_path.parent.mkdir(parents=True, exist_ok=True)

    report_path.write_text(
        report,
        encoding="utf-8",
    )

    print(
        f"Report written to: {report_path}"
    )

    # Missing specs and coverage differences are warnings. Actual generation
    # failures still fail after saving the report for inspection.
    return 1 if worker_failed or "Failed" in results.values() else 0


if __name__ == "__main__":
    raise SystemExit(main())
