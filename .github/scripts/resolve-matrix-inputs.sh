#!/usr/bin/env bash
set -euo pipefail

OUTPUT_FILE="${1:?Usage: $0 <output-file>}"

# The service catalog is the single source of truth for the service matrix.
# SERVICES_CATALOG overrides the path (used by tests).
CATALOG="${SERVICES_CATALOG:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../../config/services.json}"

# ALL_PROJECTS mirrors the Gradle subprojects in settings.gradle.kts
ALL_PROJECTS='["java","php","node","python","ruby","go","dotnet"]'
# ALL_SERVICES and EXCLUDES are derived from the catalog.
ALL_SERVICES=$(jq -c '[.services[].name | ascii_downcase]' "$CATALOG")
# A service is excluded from a project's matrix job when the project is in its
# `excludedProjects`, or when the service has a `projects` whitelist that doesn't
# contain the project. This mirrors the applicability rules in the Gradle
# conventions plugin so that no-op jobs are never scheduled.
EXCLUDES=$(jq -c --argjson allProjects "$ALL_PROJECTS" '
  [ .services[] | . as $svc
    | (if .excludedProjects != null then .excludedProjects
       elif .projects != null then ($allProjects - .projects)
       else [] end)[]
    | {project: ., service: ($svc.name | ascii_downcase)} ]
' "$CATALOG")

if [ -z "${INPUT_PROJECTS:-}" ]; then
  echo "projects=$ALL_PROJECTS" >> "$OUTPUT_FILE"
else
  JSON=$(echo "$INPUT_PROJECTS" | tr ',' '\n' | jq -Rsc 'split("\n") | map(gsub("\\s+";" ") | ltrimstr(" ") | rtrimstr(" ")) | map(select(length > 0))')
  INVALID=$(echo "$JSON" | jq -r --argjson allowed "$ALL_PROJECTS" '[.[] | select(. as $item | ($allowed | index($item)) == null)] | join(", ")')
  if [ -n "$INVALID" ]; then
    echo "::error::Invalid project(s): $INVALID. Allowed values: $(echo "$ALL_PROJECTS" | jq -r 'join(", ")')"
    exit 1
  fi
  echo "projects=$JSON" >> "$OUTPUT_FILE"
fi

if [ -z "${INPUT_SERVICES:-}" ]; then
  echo "services=$ALL_SERVICES" >> "$OUTPUT_FILE"
else
  JSON=$(echo "$INPUT_SERVICES" | tr ',' '\n' | jq -Rsc 'split("\n") | map(gsub("\\s+";" ") | ltrimstr(" ") | rtrimstr(" ")) | map(select(length > 0))')
  INVALID=$(echo "$JSON" | jq -r --argjson allowed "$ALL_SERVICES" '[.[] | select(. as $item | ($allowed | index($item)) == null)] | join(", ")')
  if [ -n "$INVALID" ]; then
    echo "::error::Invalid service(s): $INVALID. Allowed values: $(echo "$ALL_SERVICES" | jq -r 'join(", ")')"
    exit 1
  fi
  echo "services=$JSON" >> "$OUTPUT_FILE"
fi

# Emitted after input validation, so a failed run never contains an excludes line.
echo "excludes=$EXCLUDES" >> "$OUTPUT_FILE"
