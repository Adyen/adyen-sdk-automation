#!/usr/bin/env python3

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path


API_EXPLORER_BASE = "https://docs.adyen.com/api-explorer"
VERSION_PATTERN = re.compile(r"(?i)(?<![a-z0-9])v\d+(?![a-z0-9])")
MARKDOWN_LINK_PATTERN = re.compile(r"\]\(([^)]+)\)")
MARKDOWN_LINK_LABEL_PATTERN = re.compile(r"\[([^\]]+)\]\([^)]+\)")


@dataclass(frozen=True)
class ServiceMetadata:
    project: str
    service: str
    version: int
    docs_path: str
    spec: Path
    small: bool
    webhook: bool

    @property
    def service_id(self) -> str:
        return self.service.lower()

    @property
    def docs_url(self) -> str:
        if self.docs_path.startswith(("https://", "http://")):
            return self.docs_path
        return f"{API_EXPLORER_BASE}/{self.docs_path}/{self.version}/overview"


def parse_bool(value: str) -> bool:
    normalized = value.lower()
    if normalized not in {"true", "false"}:
        raise argparse.ArgumentTypeError("expected true or false")
    return normalized == "true"


def split_row(line: str) -> list[str]:
    return line.rstrip("\n").split("|")[1:-1]


def table_bounds(lines: list[str], webhook: bool) -> tuple[int, int] | None:
    heading = "## Supported Webhook versions" if webhook else None

    heading_index = None
    for index, line in enumerate(lines):
        if webhook and line.strip().lower() == heading.lower():
            heading_index = index
            break
        if not webhook and line.strip().lower() in {
            "## supported api versions",
            "## supported apis",
        }:
            heading_index = index
            break

    if heading_index is None:
        return None

    header_index = next(
        (index for index in range(heading_index + 1, len(lines)) if lines[index].lstrip().startswith("|")),
        None,
    )
    if header_index is None or header_index + 1 >= len(lines):
        raise ValueError(f"Could not find the Markdown table below {lines[heading_index].strip()}")

    first_row = header_index + 2
    end = first_row
    while end < len(lines) and lines[end].lstrip().startswith("|"):
        end += 1
    return first_row, end


def row_matches_docs_path(row: str, docs_path: str) -> bool:
    urls = MARKDOWN_LINK_PATTERN.findall(row)
    if docs_path.startswith(("https://", "http://")):
        normalized = docs_path.rstrip("/").lower()
        return any(url.rstrip("/").lower() == normalized for url in urls)

    expected_prefix = f"{API_EXPLORER_BASE}/{docs_path}/".lower()
    return any(url.lower().startswith(expected_prefix) for url in urls)


def row_matches_service_reference(row: str, metadata: ServiceMetadata) -> bool:
    reference_urls = MARKDOWN_LINK_PATTERN.findall(service_reference(metadata))
    if not reference_urls:
        return False
    row_urls = {url.rstrip("/").lower() for url in MARKDOWN_LINK_PATTERN.findall(row)}
    return any(url.rstrip("/").lower() in row_urls for url in reference_urls)


def row_matches_spec_title(row: str, spec: Path) -> bool:
    match = MARKDOWN_LINK_LABEL_PATTERN.search(row)
    if match is None:
        return False
    title, _ = read_spec_summary(spec)
    row_title = re.sub(r"[~*_]", "", match.group(1))
    return clean_title(row_title).lower() == title.lower()


def update_existing_row(row: str, metadata: ServiceMetadata, version_column: int) -> str:
    newline = "\n" if row.endswith("\n") else ""
    columns = split_row(row)
    if version_column >= len(columns):
        raise ValueError(f"Malformed supported-version row: {row.rstrip()}")

    columns[0] = MARKDOWN_LINK_PATTERN.sub(f"]({metadata.docs_url})", columns[0], count=1)

    if not VERSION_PATTERN.search(columns[version_column]):
        raise ValueError(f"Could not find a version in supported-version row: {row.rstrip()}")
    columns[version_column] = VERSION_PATTERN.sub(f"v{metadata.version}", columns[version_column], count=1)
    return "|" + "|".join(columns) + "|" + newline


def clean_title(title: str) -> str:
    return re.sub(r"^Adyen\s+", "", title).strip()


def read_spec_summary(spec: Path) -> tuple[str, str]:
    document = json.loads(spec.read_text())
    info = document.get("info", {})
    title = clean_title(str(info.get("title", "")).strip())
    description = str(info.get("description", "")).strip().split("\n\n", 1)[0]
    description = " ".join(line.removeprefix(">") for line in description.splitlines()).strip()
    description = description.replace("|", r"\|")
    if not title or not description:
        raise ValueError(f"{spec} must contain info.title and info.description")
    return title, description


def lower_camel(value: str) -> str:
    return value[:1].lower() + value[1:]


def service_reference(metadata: ServiceMetadata) -> str:
    name = metadata.service
    service_id = metadata.service_id
    camel = lower_camel(name)

    if metadata.webhook:
        if metadata.project == "java":
            return f"[{service_id}](src/main/java/com/adyen/model/{service_id})"
        if metadata.project == "dotnet":
            return f"[{name}](Adyen/{name}/Models)"
        if metadata.project == "go":
            package = re.sub(r"webhooks$", "webhook", service_id)
            return f"[{package}](src/{package})"
        if metadata.project == "node":
            return f"[{name}](src/typings/{camel})"
        if metadata.project == "php":
            return f"[{name}](src/Adyen/Model/{name})"
        raise ValueError(f"{metadata.project} does not publish webhook models in its README")

    if metadata.project == "java":
        return name
    if metadata.project == "dotnet":
        return f"[{name}](Adyen/{name})"
    if metadata.project == "go":
        return f"client.{name}()"
    if metadata.project == "node":
        path = f"{camel}Api.ts" if metadata.small else f"{camel}/index.ts"
        return f"[{name}](/src/services/{path})"
    if metadata.project == "php":
        path = f"{name}Api.php" if metadata.small else name
        return f"[{name}](src/Adyen/Service/{path})"
    if metadata.project == "python":
        return camel
    if metadata.project == "ruby":
        return f"[{name}](lib/adyen/services/{camel}.rb)"
    raise ValueError(f"Unsupported project: {metadata.project}")


def version_column(project: str, webhook: bool) -> int:
    return 1 if not webhook and project in {"node", "ruby"} else 3


def create_row(metadata: ServiceMetadata) -> str:
    title, description = read_spec_summary(metadata.spec)
    display_name = title if metadata.webhook or title.lower().endswith("api") else f"{title} API"
    api_link = f"[{display_name}]({metadata.docs_url})"
    reference = service_reference(metadata)
    version = f"v{metadata.version}" if metadata.project in {"node", "ruby"} and not metadata.webhook else f"**v{metadata.version}**"

    if not metadata.webhook and metadata.project in {"node", "ruby"}:
        return f"| {api_link} | {version} | {description} | {reference} |\n"
    return f"| {api_link} | {description} | {reference} | {version} |\n"


def update_readme(readme: Path, metadata: ServiceMetadata) -> bool:
    original = readme.read_text()
    lines = original.splitlines(keepends=True)
    bounds = table_bounds(lines, metadata.webhook)
    if bounds is None:
        print(f"Skipping {metadata.service}: {metadata.project} has no matching README table.")
        return False

    first_row, end = bounds
    matches = [
        index
        for index in range(first_row, end)
        if row_matches_docs_path(lines[index], metadata.docs_path)
        or row_matches_service_reference(lines[index], metadata)
    ]

    if len(matches) > 1:
        title_matches = [index for index in matches if row_matches_spec_title(lines[index], metadata.spec)]
        if len(title_matches) == 1:
            matches = title_matches

    if len(matches) > 1:
        raise ValueError(
            f"README contains {len(matches)} rows for documentation path {metadata.docs_path}; "
            "remove duplicates before generation"
        )

    if matches:
        index = matches[0]
        lines[index] = update_existing_row(
            lines[index],
            metadata,
            version_column(metadata.project, metadata.webhook),
        )
    else:
        lines.insert(end, create_row(metadata))

    updated = "".join(lines)
    if updated == original:
        return False

    readme.write_text(updated)
    return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Update one service in an SDK supported-version table.")
    parser.add_argument("--project", required=True)
    parser.add_argument("--readme", required=True, type=Path)
    parser.add_argument("--service", required=True)
    parser.add_argument("--version", required=True, type=int)
    parser.add_argument("--docs-path", required=True)
    parser.add_argument("--spec", required=True, type=Path)
    parser.add_argument("--small", required=True, type=parse_bool)
    parser.add_argument("--webhook", required=True, type=parse_bool)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    metadata = ServiceMetadata(
        project=args.project,
        service=args.service,
        version=args.version,
        docs_path=args.docs_path,
        spec=args.spec,
        small=args.small,
        webhook=args.webhook,
    )
    changed = update_readme(args.readme, metadata)
    print(f"{'Updated' if changed else 'No README change for'} {args.project}/{args.service}")


if __name__ == "__main__":
    main()
