#!/usr/bin/env bash
#
# This is a helper script to bootstrap the SDK projects.
#
# It clones all projects in an external dir (for development purposes and separate IDE use) and creates a symlink
# to this project.
set -euxo pipefail

BASEDIR="$(pwd)"

git_ops() {
  local repo_name="$1"
  local target="$2"
  if [[ -d "$target" ]]; then
    echo "Skipping cloning $repo_name: already exists in $target"
    return
  fi
  echo "Cloning $repo_name into $target"
  git clone "git@github.com:Adyen/$repo_name.git" "$target"
}

setup() {
  local project="$1"
  local repo_name="adyen-$project-api-library"
  local target="$BASEDIR/../$repo_name"

  git_ops "$repo_name" "$target"

  echo "Setting symlink for $project"
  rm -rf "$project/repo"
  ln -s "$target" "$project/repo"
}

# settings.gradle contains all SDKs included in this Gradle project
grep 'include(.*)' settings.gradle |
  sed 's/.*(\(.*\)).*/\1/;s/,//g' | # captures the list of SDKs
  xargs -n1 |                       # split line at single quotes
  while read -r sdk_name; do        # iterate of SDK names
    setup "${sdk_name}"             # do the setup for given SDK
  done
