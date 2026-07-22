#!/usr/bin/env python3
"""Generate a WHY-NOT registry only after runtime artifact integrity passes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

from scripts.validate_why_not_runtime import validate_run


DEFAULT_POLICY = Path("configs/benchmarks/why_not_result_registry_policy_v1.yaml")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def generate_registry(repo_root: Path, run_dir: Path) -> dict[str, Any]:
    validation = validate_run(repo_root, run_dir)
    manifest = load_json(run_dir / "run_manifest.json")
    summary = load_json(run_dir / "runtime_summary.json")
    policy = yaml.safe_load((repo_root / DEFAULT_POLICY).read_text(encoding="utf-8"))
    baseline = validation["baseline"]
    if set(policy["baselines"]) != {"W0-LINX", "W1-PRYM", "W2-PRIMAT", "W3-ABCMB"}:
        raise ValueError("result registry policy does not cover the four frozen baselines")

    slice_status = manifest["status"]
    if summary.get("numerical_consistency_status") == "batch_discrepancy_open":
        slice_status = "complete_with_batch_discrepancy_open"

    return {
        "schema_version": 1,
        "baseline": baseline,
        "source_revision": manifest["source_revision"],
        "registered_runtime_slices": 1,
        "slices": [
            {
                "scenario": "standard_fiducial",
                "status": slice_status,
                "run": run_dir.name,
                "scientific_use": manifest["scientific_use"],
                "limitations": policy["baselines"][baseline]["limitations"],
            }
        ],
        "full_baseline_status": "incomplete",
        "why_not_conclusion": "undetermined",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    registry = generate_registry(args.repo_root.resolve(), args.run_dir.resolve())
    rendered = yaml.safe_dump(registry, sort_keys=False)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(rendered, encoding="utf-8")
    temporary.replace(args.output)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
