#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: $0 <empty-destination-directory>" >&2
  exit 2
fi

destination=$1
if [[ -e "$destination" ]] && [[ -n "$(find "$destination" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ]]; then
  echo "destination must be absent or empty: $destination" >&2
  exit 2
fi
mkdir -p "$destination"

fetch_exact() {
  local name=$1
  local repository=$2
  local revision=$3
  local target="$destination/$name"

  git clone --filter=blob:none --no-checkout "$repository" "$target"
  git -C "$target" checkout --detach "$revision"
  if [[ "$(git -C "$target" rev-parse HEAD)" != "$revision" ]]; then
    echo "revision mismatch for $name" >&2
    exit 1
  fi
  git -C "$target" submodule update --init --recursive
  echo "Verified $name $revision"
}

fetch_exact LINX https://github.com/cgiovanetti/LINX.git \
  ec2e9d2ca455e8204137e884da29f5dd13a638fa
fetch_exact PRyMordial https://github.com/vallima/PRyMordial.git \
  725d8a8db3ad5ea2630580d825c9d0d69ed76533
fetch_exact PRIMAT https://github.com/CyrilPitrou/primat.git \
  21ff8f39fa18e3937e9fdf386cfa982361bfdfce
fetch_exact ABCMB https://github.com/TonyZhou729/ABCMB.git \
  5eabbab4ed7e53f264e16024743d1ba517845c37

echo "All WHY-NOT baselines fetched at the frozen revisions."
