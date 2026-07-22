#!/usr/bin/env python3
"""Validate the pinned UQ0 public-solver registry and its evidence bindings."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

import yaml


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
REVISION_RE = re.compile(r"^[0-9a-f]{40}$")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return payload


def require_hash(root: Path, record: dict[str, Any], label: str) -> None:
    relative = Path(record["path"])
    expected = str(record["sha256"])
    if not SHA256_RE.fullmatch(expected):
        raise ValueError(f"{label} has an invalid SHA-256: {expected!r}")
    actual = sha256(root / relative)
    if actual != expected:
        raise ValueError(f"{label} hash mismatch: {actual} != {expected}")


def validate_card(root: Path, card_path: Path, expected_id: str) -> dict[str, Any]:
    card = load_yaml(card_path)
    if card.get("card_id") != expected_id:
        raise ValueError(f"{card_path} card_id does not match registry")
    if card.get("status") != "accepted_for_uq0_public_forward_baseline":
        raise ValueError(f"{expected_id} is not accepted for the UQ0 forward baseline")

    source = card["source"]
    if not REVISION_RE.fullmatch(str(source["revision"])):
        raise ValueError(f"{expected_id} lacks a full pinned source revision")
    if not source.get("repository") or not source.get("license"):
        raise ValueError(f"{expected_id} lacks repository or license metadata")

    environment = card["environment"]
    environment_lock = root / environment["lock"]
    if sha256(environment_lock) != environment["lock_sha256"]:
        raise ValueError(f"{expected_id} environment lock hash mismatch")
    if environment.get("precision") != "float64":
        raise ValueError(f"{expected_id} is not bound to float64")

    config = card["accepted_configuration"]
    if sha256(root / config["config"]) != config["config_sha256"]:
        raise ValueError(f"{expected_id} accepted configuration hash mismatch")
    if (
        "adapter_config" in config
        and sha256(root / config["adapter_config"]) != config["adapter_config_sha256"]
    ):
        raise ValueError(f"{expected_id} adapter configuration hash mismatch")

    for output in ("Y_p", "D_over_H"):
        record = card["outputs"][output]
        if not math.isfinite(float(record["value"])) or float(record["value"]) <= 0:
            raise ValueError(f"{expected_id} has invalid {output}")
        if not record.get("unit") or not record.get("artifact_key"):
            raise ValueError(f"{expected_id} lacks {output} convention metadata")

    runtime_values = [
        float(value)
        for key, value in card["runtime"].items()
        if key.endswith("seconds") and not key.startswith("structured")
    ]
    if not runtime_values or any(value <= 0 for value in runtime_values):
        raise ValueError(f"{expected_id} lacks positive runtime measurements")

    failure = card["structured_failure_contract"]
    ledger = root / failure["ledger"]
    if sha256(ledger) != failure["ledger_sha256"]:
        raise ValueError(f"{expected_id} failure-ledger hash mismatch")
    if failure.get("format") != "json_lines" or failure.get("nonfinite_policy") != "reject":
        raise ValueError(f"{expected_id} does not enforce structured non-finite rejection")
    implementation = root / failure["implementation"]
    implementation_text = implementation.read_text(encoding="utf-8")
    if "failures" not in implementation_text or "traceback" not in implementation_text:
        raise ValueError(f"{expected_id} failure implementation is not auditable")

    for label, record in card["evidence"].items():
        require_hash(root, record, f"{expected_id}:{label}")

    manifest_record = card["evidence"]["manifest"]
    manifest = json.loads((root / manifest_record["path"]).read_text(encoding="utf-8"))
    if manifest[manifest_record["source_revision_field"]] != source["revision"]:
        raise ValueError(f"{expected_id} manifest source revision mismatch")
    if manifest[manifest_record["config_hash_field"]] != config["config_sha256"]:
        raise ValueError(f"{expected_id} manifest configuration hash mismatch")

    return {
        "path_id": expected_id,
        "source_revision": source["revision"],
        "status": "accepted_for_uq0_public_forward_baseline",
    }


def validate_registry(registry_path: Path, root: Path) -> dict[str, Any]:
    registry = load_yaml(registry_path)
    paths = registry.get("paths", [])
    accepted = [record for record in paths if record.get("uq0_accepted") is True]
    minimum = int(registry["acceptance_contract"]["minimum_paths"])
    if len(accepted) < minimum or registry.get("accepted_path_count") != len(accepted):
        raise ValueError("UQ0 registry does not contain the declared minimum accepted paths")
    if len({record["path_id"] for record in accepted}) != len(accepted):
        raise ValueError("UQ0 registry path IDs are not unique")

    standard_point = registry["shared_contracts"]["historical_standard_point"]
    if sha256(root / standard_point["path"]) != standard_point["sha256"]:
        raise ValueError("historical standard-point schema hash mismatch")

    results = [validate_card(root, root / record["card"], record["path_id"]) for record in accepted]
    if len({record["source_revision"] for record in results}) != len(results):
        raise ValueError("accepted paths do not have distinct pinned source revisions")
    return {
        "accepted_path_count": len(results),
        "registry_id": registry["registry_id"],
        "status": "pass",
        "paths": results,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--registry",
        type=Path,
        default=Path("configs/solvers/public_bbn_baselines_UQ0_v1.yaml"),
    )
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    registry = args.registry
    if not registry.is_absolute():
        registry = args.repo_root / registry
    print(json.dumps(validate_registry(registry, args.repo_root), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
