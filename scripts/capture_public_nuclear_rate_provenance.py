#!/usr/bin/env python3
"""Capture hashes for public solver-distributed nuclear-rate tables."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(repo: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *arguments],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return completed.stdout.strip()


def validate_protocol(protocol: dict[str, Any]) -> None:
    if protocol.get("schema_version") != 1:
        raise ValueError("unsupported provenance schema")
    if protocol.get("inventory_id") != "PUBLIC-NUCLEAR-RATE-PROVENANCE-v1":
        raise ValueError("unexpected provenance inventory id")
    if protocol.get("status") != "protocol_frozen_capture_pending":
        raise ValueError("provenance protocol is not frozen for capture")
    repositories = protocol.get("repositories")
    if not isinstance(repositories, dict) or set(repositories) != {
        "LINX",
        "PRyMordial",
        "PRIMAT",
        "ABCMB",
    }:
        raise ValueError("the four registered public repositories are required")
    reaction_tokens = protocol.get("reaction_path_tokens")
    if not isinstance(reaction_tokens, dict) or set(reaction_tokens) != {
        "dp_gamma_he3",
        "dd_n_he3",
        "dd_p_t",
    }:
        raise ValueError("the three registered head reactions are required")

    all_paths: list[str] = []
    for repository, specification in repositories.items():
        revision = specification.get("revision")
        collections = specification.get("collections")
        if not isinstance(revision, str) or len(revision) != 40:
            raise ValueError(f"{repository} has no full frozen revision")
        if not isinstance(collections, dict) or not collections:
            raise ValueError(f"{repository} has no registered collections")
        for collection, paths in collections.items():
            if not isinstance(paths, list) or not paths:
                raise ValueError(f"{repository}/{collection} has no files")
            for raw_path in paths:
                candidate = Path(raw_path)
                if candidate.is_absolute() or ".." in candidate.parts:
                    raise ValueError(f"unsafe source path: {raw_path}")
                all_paths.append(raw_path)
            for reaction, tokens in reaction_tokens.items():
                if not any(any(token in raw_path for token in tokens) for raw_path in paths):
                    raise ValueError(
                        f"{repository}/{collection} omits registered reaction {reaction}"
                    )
    if len(all_paths) != len(set(all_paths)):
        raise ValueError("source paths must be unique within the inventory")
    minimum = int(protocol["acceptance"]["minimum_total_files"])
    if len(all_paths) < minimum:
        raise ValueError(f"only {len(all_paths)} files registered; minimum is {minimum}")


def capture_repository(
    source_root: Path, repository: str, specification: dict[str, Any]
) -> dict[str, Any]:
    repo = (source_root / repository).resolve()
    if not (repo / ".git").exists():
        raise FileNotFoundError(f"missing Git checkout: {repo}")
    revision = git(repo, "rev-parse", "HEAD")
    if revision != specification["revision"]:
        raise ValueError(f"{repository} revision {revision} != frozen {specification['revision']}")
    porcelain = git(repo, "status", "--porcelain", "--untracked-files=no")
    if porcelain:
        raise ValueError(f"{repository} tracked source checkout is dirty")

    collections: dict[str, list[dict[str, Any]]] = {}
    for collection, paths in specification["collections"].items():
        captured: list[dict[str, Any]] = []
        for raw_path in paths:
            path = repo / raw_path
            if path.is_symlink() or not path.is_file():
                raise ValueError(f"source must be a regular non-symlink file: {path}")
            git(repo, "cat-file", "-e", f"HEAD:{raw_path}")
            raw = path.read_bytes()
            captured.append(
                {
                    "path": raw_path,
                    "git_blob": git(repo, "rev-parse", f"HEAD:{raw_path}"),
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "size_bytes": len(raw),
                    "line_count": len(raw.splitlines()),
                }
            )
        collections[collection] = captured
    return {
        "revision": revision,
        "license": specification["license"],
        "tracked_tree": git(repo, "rev-parse", "HEAD^{tree}"),
        "collections": collections,
    }


def capture(config: Path, source_root: Path) -> dict[str, Any]:
    protocol = yaml.safe_load(config.read_text(encoding="utf-8"))
    validate_protocol(protocol)
    repositories = {
        name: capture_repository(source_root, name, specification)
        for name, specification in protocol["repositories"].items()
    }
    file_count = sum(
        len(files)
        for repository in repositories.values()
        for files in repository["collections"].values()
    )
    digest_to_locations: dict[str, list[str]] = {}
    for repository_name, repository in repositories.items():
        for collection_name, files in repository["collections"].items():
            for item in files:
                digest_to_locations.setdefault(item["sha256"], []).append(
                    f"{repository_name}/{collection_name}/{item['path']}"
                )
    duplicate_groups = [
        {"sha256": digest, "locations": locations}
        for digest, locations in sorted(digest_to_locations.items())
        if len(locations) > 1
    ]
    return {
        "schema_version": 1,
        "inventory_id": protocol["inventory_id"],
        "status": "captured_inventory_only_not_nuc_freeze",
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "config": str(config.resolve()),
        "config_sha256": sha256(config),
        "source_root": str(source_root.resolve()),
        "file_count": file_count,
        "repositories": repositories,
        "duplicate_content_groups": duplicate_groups,
        "scientific_boundary": protocol["scientific_boundary"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = capture(args.config.resolve(), args.source_root.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
