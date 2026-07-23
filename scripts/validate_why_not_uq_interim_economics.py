#!/usr/bin/env python3
"""Validate frozen non-decisional UQ runtime reference arithmetic."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

try:
    from scripts.validate_why_not_runtime import validate_run
except ModuleNotFoundError:  # Direct ``python scripts/<name>.py`` execution.
    from validate_why_not_runtime import validate_run


EXPECTED_ARTIFACT_SHA256 = "d873da7ae5cf53e26a011aa661884244d19199698d4b3afdb324a49d2d5b0a70"
EXPECTED_BASELINES = {"W0-LINX", "W1-PRYM", "W2-PRIMAT", "W3-ABCMB"}
EXPECTED_CALL_COUNTS = [1_000, 10_000, 64_000]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(path: Path, repository_root: Path) -> dict[str, Any]:
    if sha256(path) != EXPECTED_ARTIFACT_SHA256:
        raise ValueError("interim UQ economics artifact SHA256 drift")
    artifact = json.loads(path.read_text(encoding="utf-8"))
    if artifact["schema_version"] != 1:
        raise ValueError("unsupported interim UQ economics schema")
    if artifact["artifact_id"] != "WHY-NOT-UQ-INTERIM-ECONOMICS-v1":
        raise ValueError("unexpected interim UQ economics artifact")
    if artifact["task_id"] != "P0-WHY-NOT-01":
        raise ValueError("interim UQ economics task drift")
    if artifact["status"] != "interim_reference_arithmetic_full_UQ_economics_undetermined":
        raise ValueError("interim UQ economics status overclaim")

    protocol = artifact["protocol"]
    protocol_path = repository_root / protocol["path"]
    if sha256(protocol_path) != protocol["sha256"]:
        raise ValueError("WHY-NOT protocol SHA256 drift")

    baselines = artifact["baselines"]
    if len(baselines) != 4 or {item["baseline_id"] for item in baselines} != EXPECTED_BASELINES:
        raise ValueError("interim baseline coverage drift")
    for baseline in baselines:
        for source in baseline["source_artifacts"].values():
            if sha256(repository_root / source["path"]) != source["sha256"]:
                raise ValueError("interim source artifact SHA256 drift")
        run_root = (
            repository_root
            / "artifacts/benchmarks/WHY-NOT-EXISTING-SOLVERS-v1"
            / baseline["baseline_id"]
            / baseline["run_directory"]
        )
        manifest = json.loads((run_root / "run_manifest.json").read_text(encoding="utf-8"))
        if baseline["run_id"] != manifest["run_id"]:
            raise ValueError("runtime UUID lineage drift")
        integrity = validate_run(repository_root, run_root)
        expected_integrity = {
            "validation_status": integrity["validation_status"],
            "checks": integrity["checks"],
            "successful_warm_points": integrity["successful_warm_points"],
            "timed_warm_points_expected": integrity["timed_warm_points_expected"],
            "failure_records": integrity["failure_records"],
        }
        if baseline["raw_runtime_integrity"] != expected_integrity:
            raise ValueError("raw runtime integrity report drift")
        if baseline["full_baseline_status"] != "incomplete":
            raise ValueError("interim reference arithmetic hides a completed baseline")
        if baseline["why_not_conclusion"] != "undetermined":
            raise ValueError("interim reference arithmetic manufactures a WHY-NOT conclusion")

        measured = baseline["measured_standard_fiducial"]
        if measured["structured_failures"] != 0:
            raise ValueError("frozen runtime slice failure-count drift")
        scalar_seconds = float(measured["warm_scalar_median_seconds_per_point"])
        workload_seconds = float(measured["warm_64_workload_median_seconds"])
        workload_per_point = float(measured["warm_64_workload_median_seconds_per_point"])
        if not math.isclose(
            workload_per_point,
            workload_seconds / 64.0,
            rel_tol=0.0,
            abs_tol=1.0e-15,
        ):
            raise ValueError("64-point workload arithmetic drift")
        price = float(measured["hourly_price_cny"])
        for projections, seconds_per_point in (
            (baseline["scalar_path_reference_arithmetic"], scalar_seconds),
            (
                baseline["measured_64_workload_reference_arithmetic"],
                workload_per_point,
            ),
        ):
            if [row["call_equivalents"] for row in projections] != EXPECTED_CALL_COUNTS:
                raise ValueError("call-equivalent scenario drift")
            for row in projections:
                expected_hours = int(row["call_equivalents"]) * seconds_per_point / 3600.0
                if not math.isclose(
                    float(row["reference_worker_hours_if_identical_call_cost"]),
                    expected_hours,
                    rel_tol=0.0,
                    abs_tol=1.0e-15,
                ):
                    raise ValueError("worker-hour reference arithmetic drift")
                if not math.isclose(
                    float(row["reference_cost_cny_if_identical_call_cost"]),
                    expected_hours * price,
                    rel_tol=0.0,
                    abs_tol=1.0e-15,
                ):
                    raise ValueError("cost reference arithmetic drift")
        boundary = baseline["reference_arithmetic_boundary"]
        if boundary != {
            "not_a_UQ_cost_projection": True,
            "q_varying_abundance_calls_measured": False,
            "rate_marginalization_measured": False,
            "posterior_recovery_measured": False,
            "SBC_measured": False,
            "two_worker_scaling_measured": False,
            "production_candidate_runtime_measured": False,
            "warm_standard_point_linear_extrapolation_only": True,
        }:
            raise ValueError("reference arithmetic boundary drift")

    if artifact["decision"] != {
        "direct_solver_sufficient": "undetermined",
        "emulator_speed_necessity": "undetermined",
        "direct_first_stop_rule_evaluable": False,
        "reason": (
            "Only standard-fiducial forward runtime is measured. The arithmetic is not a "
            "UQ cost projection; actual R0 rate draws, native marginalization, posterior "
            "calls, SBC, fidelity, accepted-config retiming and scaling are pending."
        ),
    }:
        raise ValueError("interim decision boundary drift")
    if artifact["claim_boundary"] != {
        "P0_WHY_NOT_01_done_allowed": False,
        "progress_credit_memos": 0,
        "UQ0_R0_prior_gate_bypassed": False,
        "production_run_authorized": False,
        "scientific_signoff_provided": False,
    }:
        raise ValueError("interim claim boundary drift")
    return {
        "baselines": len(baselines),
        "reference_arithmetic_paths": len(baselines) * 2,
        "reference_arithmetic_scenarios": (len(baselines) * 2 * len(EXPECTED_CALL_COUNTS)),
        "why_not_conclusion": artifact["decision"]["direct_solver_sufficient"],
        "progress_credit_memos": artifact["claim_boundary"]["progress_credit_memos"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    print(
        json.dumps(
            validate(args.artifact, args.repository_root.resolve()),
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
