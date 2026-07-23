#!/usr/bin/env python3
"""Validate the committed public solver-rate provenance capture fail-closed."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import yaml


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from scripts.capture_public_nuclear_rate_provenance import validate_protocol


INVENTORY_ID = "PUBLIC-NUCLEAR-RATE-PROVENANCE-v1"
CAPTURE_STATUS = "captured_inventory_only_not_nuc_freeze"
COMMITTED_CAPTURE_SHA256 = (
    "7c79a1e9569c5ee82c41c04be086c6adb1214ecaf9efc3f9cdff0e38dcbf63c2"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate(config_path: Path, artifact_path: Path) -> dict[str, Any]:
    require(sha256(artifact_path) == COMMITTED_CAPTURE_SHA256, "capture hash drift")
    protocol = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    validate_protocol(protocol)
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))

    require(artifact.get("schema_version") == 1, "artifact schema drift")
    require(artifact.get("inventory_id") == INVENTORY_ID, "artifact identity drift")
    require(artifact.get("status") == CAPTURE_STATUS, "artifact status drift")
    require(artifact.get("config_sha256") == sha256(config_path), "config hash drift")
    require(
        Path(str(artifact.get("config", ""))).name == config_path.name,
        "captured config path drift",
    )
    require(
        artifact.get("scientific_boundary") == protocol["scientific_boundary"],
        "scientific boundary drift",
    )

    repositories = artifact.get("repositories")
    require(
        isinstance(repositories, dict)
        and set(repositories) == set(protocol["repositories"]),
        "repository set drift",
    )

    locations_by_digest: dict[str, list[str]] = {}
    file_count = 0
    for repository_name, specification in protocol["repositories"].items():
        captured = repositories[repository_name]
        require(captured.get("revision") == specification["revision"], "revision drift")
        require(captured.get("license") == specification["license"], "license drift")
        require(
            isinstance(captured.get("tracked_tree"), str)
            and len(captured["tracked_tree"]) == 40,
            "tracked tree is not a full Git object id",
        )
        collections = captured.get("collections")
        require(
            isinstance(collections, dict)
            and set(collections) == set(specification["collections"]),
            "collection set drift",
        )
        for collection_name, expected_paths in specification["collections"].items():
            records = collections[collection_name]
            require(isinstance(records, list), "collection records are not a list")
            require(
                [record.get("path") for record in records] == expected_paths,
                "captured path/order drift",
            )
            for record in records:
                digest = record.get("sha256")
                require(
                    isinstance(digest, str) and len(digest) == 64,
                    "invalid SHA256 record",
                )
                require(
                    isinstance(record.get("git_blob"), str)
                    and len(record["git_blob"]) == 40,
                    "invalid Git blob record",
                )
                require(
                    isinstance(record.get("size_bytes"), int)
                    and record["size_bytes"] > 0,
                    "invalid byte count",
                )
                require(
                    isinstance(record.get("line_count"), int)
                    and record["line_count"] > 0,
                    "invalid line count",
                )
                locations_by_digest.setdefault(digest, []).append(
                    f"{repository_name}/{collection_name}/{record['path']}"
                )
                file_count += 1

    expected_duplicates = [
        {"sha256": digest, "locations": locations}
        for digest, locations in sorted(locations_by_digest.items())
        if len(locations) > 1
    ]
    require(artifact.get("file_count") == file_count, "file count drift")
    require(
        artifact.get("duplicate_content_groups") == expected_duplicates,
        "duplicate content grouping drift",
    )
    require(
        file_count >= int(protocol["acceptance"]["minimum_total_files"]),
        "capture is below the minimum file count",
    )

    return {
        "accepted": True,
        "artifact_id": INVENTORY_ID,
        "duplicate_content_groups": len(expected_duplicates),
        "file_count": file_count,
        "nuc_v1_frozen": False,
        "repositories": len(repositories),
        "status": CAPTURE_STATUS,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/physics/public_nuclear_rate_provenance_v1.yaml"),
    )
    args = parser.parse_args()
    print(json.dumps(validate(args.config, args.artifact), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
