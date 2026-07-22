#!/usr/bin/env python3
"""Validate one WHY-NOT runtime slice without granting scientific acceptance."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import yaml

COMMON_PROTOCOL = Path("configs/benchmarks/why_not_existing_solvers_v1.yaml")
PARAMETER_SCHEMA = Path("configs/physics/parameter_schema.yaml")
ADAPTER_CONFIGS = {
    "W1-PRYM": Path("configs/benchmarks/prymordial_runtime_adapter_v1.yaml"),
    "W3-ABCMB": Path("configs/benchmarks/abcmb_linx_runtime_adapter_v1.yaml"),
}
NATIVE_BATCH_BASELINES = {"W0-LINX", "W3-ABCMB"}
SEQUENTIAL_BATCH_BASELINES = {"W1-PRYM", "W2-PRIMAT"}


class ValidationError(RuntimeError):
    """Raised when an artifact violates its registered runtime contract."""


def quantile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def summarize(values: list[float]) -> dict[str, float]:
    require(bool(values), "cannot summarize an empty timing sequence")
    return {
        "median": quantile(values, 0.5),
        "q1": quantile(values, 0.25),
        "q3": quantile(values, 0.75),
        "p95": quantile(values, 0.95),
        "minimum": min(values),
        "maximum": max(values),
    }


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def require_close(actual: float, expected: float, label: str) -> None:
    require(
        math.isclose(actual, expected, rel_tol=1.0e-12, abs_tol=1.0e-15),
        f"{label}: {actual} != {expected}",
    )


def validate_run(repo_root: Path, run_dir: Path) -> dict[str, Any]:
    required_files = {
        "failures.jsonl",
        "posterior_metrics.json",
        "resource_report.json",
        "run_manifest.json",
        "runtime_summary.json",
        "timings.jsonl",
    }
    missing = sorted(name for name in required_files if not (run_dir / name).is_file())
    require(not missing, f"missing runtime artifacts: {missing}")

    protocol_path = repo_root / COMMON_PROTOCOL
    schema_path = repo_root / PARAMETER_SCHEMA
    protocol = yaml.safe_load(protocol_path.read_text(encoding="utf-8"))
    manifest = load_json(run_dir / "run_manifest.json")
    summary = load_json(run_dir / "runtime_summary.json")
    resources = load_json(run_dir / "resource_report.json")
    posterior = load_json(run_dir / "posterior_metrics.json")
    timings = load_jsonl(run_dir / "timings.jsonl")
    failures = load_jsonl(run_dir / "failures.jsonl")

    baseline = manifest["baseline"]
    require(baseline in protocol["baselines"], f"unregistered baseline: {baseline}")
    registered = protocol["baselines"][baseline]
    expected_repetitions = int(protocol["execution"]["warm_repetitions"])
    expected_batch_sizes = [int(value) for value in protocol["execution"]["batch_sizes"]]

    checks: list[str] = []

    def checked(condition: bool, message: str, check_id: str) -> None:
        require(condition, message)
        checks.append(check_id)

    checked(
        manifest["config_sha256"] == sha256(protocol_path),
        "common protocol hash mismatch",
        "common_protocol_hash",
    )
    checked(
        manifest["parameter_schema_sha256"] == sha256(schema_path),
        "parameter schema hash mismatch",
        "parameter_schema_hash",
    )
    checked(
        manifest["source_revision"] == registered["revision"],
        "source revision mismatch",
        "source_revision",
    )
    checked(
        manifest["scientific_use"] == "registered_standard_fiducial_runtime_slice_only",
        "runtime slice scientific boundary mismatch",
        "scientific_boundary",
    )
    checked(
        manifest["repetitions"] == expected_repetitions,
        "warm repetition count mismatch",
        "repetition_contract",
    )
    checked(
        manifest["batch_sizes"] == expected_batch_sizes,
        "batch size contract mismatch",
        "batch_contract",
    )

    lock_relative = Path(protocol["execution"]["environment_locks"][baseline])
    checked(
        manifest["environment_lock_sha256"] == sha256(repo_root / lock_relative),
        "environment lock hash mismatch",
        "environment_lock_hash",
    )

    adapter_relative = ADAPTER_CONFIGS.get(baseline)
    if adapter_relative is None:
        checked(
            manifest.get("adapter_config_sha256") in (None, ""),
            "unexpected adapter config for baseline",
            "adapter_absent_as_registered",
        )
    else:
        checked(
            manifest.get("adapter_config_sha256") == sha256(repo_root / adapter_relative),
            "adapter config hash mismatch",
            "adapter_config_hash",
        )

    cold_import = [record for record in timings if record["kind"] == "cold_import"]
    cold_solve = [record for record in timings if record["kind"] == "cold_solve"]
    cold_batch = [record for record in timings if record["kind"] == "cold_batch_compile_and_solve"]
    warm = [record for record in timings if record["kind"] == "warm_batch"]
    scalar = [record for record in warm if record["batch_size"] == 1]
    batch = [record for record in warm if record["batch_size"] == 64]

    checked(len(cold_import) == 1, "expected exactly one cold import", "cold_import_record")
    checked(len(cold_solve) == 1, "expected exactly one cold solve", "cold_solve_record")
    checked(
        len(scalar) == expected_repetitions,
        "scalar timing count mismatch",
        "scalar_timing_records",
    )
    checked(
        len(batch) == expected_repetitions,
        "batch timing count mismatch",
        "batch_timing_records",
    )
    if baseline in NATIVE_BATCH_BASELINES:
        checked(len(cold_batch) == 1, "native batch compile record missing", "native_batch_compile")
        checked(
            all(record["execution_mode"] == "jax_jit_vmap_native_batch" for record in batch),
            "native batch execution mode mismatch",
            "native_batch_mode",
        )
    elif baseline in SEQUENTIAL_BATCH_BASELINES:
        checked(not cold_batch, "sequential baseline has native batch compile", "no_native_batch")
        checked(
            all(
                record["execution_mode"] == "sequential_calls_no_native_batch_api"
                for record in batch
            ),
            "sequential batch execution mode mismatch",
            "sequential_batch_mode",
        )
    else:  # pragma: no cover - protected by registered baseline sets
        raise ValidationError(f"baseline batch semantics are not registered: {baseline}")

    checked(
        all(record["status"] in {"ok", "failed"} for record in warm),
        "unknown warm timing status",
        "structured_warm_status",
    )
    checked(
        len(failures) == int(resources["failure_count"]),
        "failure ledger and resource count disagree",
        "failure_count_consistency",
    )
    expected_status = "complete" if not failures else "complete_with_failures"
    checked(
        manifest["status"] == expected_status,
        "manifest completion status disagrees with failures",
        "manifest_failure_status",
    )

    scalar_summary = summarize([float(record["elapsed_seconds"]) for record in scalar])
    batch_summary = summarize([float(record["elapsed_seconds"]) for record in batch])
    for label, derived in (("warm_batch_1", scalar_summary), ("warm_batch_64", batch_summary)):
        for statistic, expected in derived.items():
            require_close(
                float(summary["timings_seconds"][label][statistic]),
                expected,
                f"{label}.{statistic}",
            )
    checks.append("timing_summary_recomputed")

    checked(
        posterior["status"] == "not_run",
        "runtime slice must not contain unregistered posterior evidence",
        "posterior_boundary",
    )
    checked(
        float(resources["gpu_hours"]) == 0.0,
        "CPU runtime slice reports nonzero GPU hours",
        "gpu_boundary",
    )
    require_close(
        float(resources["estimated_cost_cny"]),
        float(resources["worker_hours"]) * float(resources["hourly_price_cny"]),
        "estimated_cost_cny",
    )
    checks.append("cost_recomputed")

    successful_points = sum(int(record["successful_points"]) for record in warm)
    expected_points = expected_repetitions * sum(expected_batch_sizes)
    report = {
        "baseline": baseline,
        "checks": checks,
        "failure_records": len(failures),
        "manifest_status": manifest["status"],
        "maximum_absolute_repeat_drift": summary["maximum_absolute_repeat_drift"],
        "run": run_dir.name,
        "schema_version": 1,
        "scientific_use": "artifact_integrity_only_not_scientific_acceptance",
        "successful_warm_points": successful_points,
        "timed_warm_points_expected": expected_points,
        "timings": {
            "batch_64_median_seconds": batch_summary["median"],
            "batch_64_median_seconds_per_point": batch_summary["median"] / 64,
            "batch_64_p95_seconds": batch_summary["p95"],
            "scalar_median_seconds": scalar_summary["median"],
            "scalar_p95_seconds": scalar_summary["p95"],
        },
        "validation_status": "passed",
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    report = validate_run(args.repo_root.resolve(), args.run_dir.resolve())
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
