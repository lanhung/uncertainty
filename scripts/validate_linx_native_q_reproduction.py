#!/usr/bin/env python3
"""Fail-closed validator for the LINX native-q abundance reproduction."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import yaml


ARTIFACT_ID = "LINX-NATIVE-Q-REPRODUCTION-v1"
EXPECTED_REVISION = "ec2e9d2ca455e8204137e884da29f5dd13a638fa"
EXPECTED_CONFIG_SHA256 = "d55d7a9775f1e9a7e4fa41a9869870631137528714dce50051558795e55497b7"
EXPECTED_MAPPING_SHA256 = "6a958225feb3cc531753571c582376a0c5cf3404c1a4e6643482a0d8114e7418"
EXPECTED_PARAMETER_SHA256 = "4dfbf65ee04e4ab6502e18bf6b69c78a447c9c8d8db660033f2c03b560e04d7a"
EXPECTED_OBSERVATION_SHA256 = "02a4a5453afff34c7f1f036a33d46e728d49a954d46a34e52aa45a570f6f7a8c"
EXPECTED_LOCK_SHA256 = "98c8f6de35dfdf7147857a3c28153b10f3ad7d424cb9faeea15de75cacd27556"
OUTPUT_KEYS = ("Neff", "YPBBN", "DoH", "He3oH", "Li7oH")
NORMALIZED_KEYS = ("YPBBN", "DoH")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest_json(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def _values(row: dict[str, Any]) -> dict[str, float]:
    return {key: float(row["outputs"][key]) for key in OUTPUT_KEYS}


def _absolute_max(left: dict[str, float], right: dict[str, float]) -> float:
    return max(abs(left[key] - right[key]) for key in OUTPUT_KEYS)


def _normalized_max(
    left: dict[str, float],
    right: dict[str, float],
    sigmas: dict[str, float],
) -> float:
    return max(abs(left[key] - right[key]) / sigmas[key] for key in NORMALIZED_KEYS)


def recompute_decision(protocol: dict[str, Any], results: dict[str, Any]) -> dict[str, Any]:
    """Independent acceptance recomputation; stored decisions are not trusted."""
    scalar_rows = results["scalar_rows"]
    batch_rows = results["batch_rows"]
    failures = int(results["structured_failure_count"])
    sigmas = {key: float(value) for key, value in results["observation_sigmas"].items()}
    if set(sigmas) != set(NORMALIZED_KEYS) or any(
        not math.isfinite(value) or value <= 0.0 for value in sigmas.values()
    ):
        raise ValueError("invalid observation normalization")

    acceptance = protocol["acceptance"]
    cases = [str(case["id"]) for case in protocol["numerical_cases"]]
    q_records = protocol["q_contract"]["vectors"]
    q_ids = [str(record["id"]) for record in q_records]
    q_length = int(protocol["q_contract"]["vector_length"])
    expected_vectors: dict[str, list[float]] = {}
    indices = {
        str(key): int(value) for key, value in protocol["q_contract"]["indices_zero_based"].items()
    }
    for record in q_records:
        vector = [0.0] * q_length
        if record["reaction"] != "central":
            vector[indices[str(record["reaction"])]] = float(record["q"])
        expected_vectors[str(record["id"])] = vector

    scalar: dict[tuple[str, str, int], dict[str, Any]] = {}
    for row in scalar_rows:
        key = (str(row["case_id"]), str(row["q_id"]), int(row["repetition"]))
        if key in scalar:
            raise ValueError(f"duplicate scalar row: {key}")
        if row.get("mode") != "scalar" or row.get("q_vector") != expected_vectors.get(key[1]):
            raise ValueError("scalar row q-vector/mode drift")
        scalar[key] = row
    scalar_repetitions = int(protocol["execution"]["scalar_repetitions_per_case_q"])
    expected_scalar = {
        (case_id, q_id, repetition)
        for case_id in cases
        for q_id in q_ids
        for repetition in range(scalar_repetitions)
    }
    scalar_complete = set(scalar) == expected_scalar

    heterogeneous = protocol["execution"]["heterogeneous_batch"]
    batch_case = str(heterogeneous["numerical_case"])
    duplicate_count = int(heterogeneous["duplicate_each_q_vector"])
    batch_repetitions = int(heterogeneous["warm_repetitions"])
    expected_batch = {
        (repetition, q_id, duplicate)
        for repetition in range(batch_repetitions)
        for q_id in q_ids
        for duplicate in range(duplicate_count)
    }
    expected_batch_order = [
        (repetition, str(q_id), duplicate)
        for repetition in range(batch_repetitions)
        for q_id in heterogeneous["q_vector_order"]
        for duplicate in range(duplicate_count)
    ]
    batch: dict[tuple[int, str, int], dict[str, Any]] = {}
    for row_index, row in enumerate(batch_rows):
        key = (int(row["repetition"]), str(row["q_id"]), int(row["duplicate"]))
        if key in batch:
            raise ValueError(f"duplicate batch row: {key}")
        expected_key = (
            expected_batch_order[row_index] if row_index < len(expected_batch_order) else None
        )
        if (
            row.get("mode") != "heterogeneous_batch"
            or row.get("case_id") != batch_case
            or row.get("q_vector") != expected_vectors.get(key[1])
            or row.get("row_index") != row_index
            or key != expected_key
        ):
            raise ValueError("batch row order/q-vector/mode/case drift")
        batch[key] = row
    batch_complete = set(batch) == expected_batch

    finite_outputs = True
    positive_protons = True
    row_status_ok = True
    for row in scalar_rows + batch_rows:
        outputs = row.get("outputs", {})
        finite_outputs &= set(outputs) == set(OUTPUT_KEYS)
        finite_outputs &= all(
            math.isfinite(float(outputs.get(key, math.nan))) for key in OUTPUT_KEYS
        )
        proton = float(row.get("proton_denominator", math.nan))
        positive_protons &= math.isfinite(proton) and proton > 0.0
        row_status_ok &= row.get("status") == "ok"

    scalar_repeat = math.inf
    if scalar_complete:
        scalar_repeat = 0.0
        for case_id in cases:
            for q_id in q_ids:
                reference = _values(scalar[(case_id, q_id, 0)])
                for repetition in range(1, scalar_repetitions):
                    scalar_repeat = max(
                        scalar_repeat,
                        _absolute_max(
                            reference,
                            _values(scalar[(case_id, q_id, repetition)]),
                        ),
                    )

    batch_repeat = math.inf
    if batch_complete:
        batch_repeat = 0.0
        for q_id in q_ids:
            reference = _values(batch[(0, q_id, 0)])
            for repetition in range(batch_repetitions):
                for duplicate in range(duplicate_count):
                    batch_repeat = max(
                        batch_repeat,
                        _absolute_max(
                            reference,
                            _values(batch[(repetition, q_id, duplicate)]),
                        ),
                    )

    scalar_batch = math.inf
    if scalar_complete and batch_complete:
        scalar_batch = 0.0
        for q_id in q_ids:
            reference = _values(scalar[(batch_case, q_id, 0)])
            for repetition in range(batch_repetitions):
                for duplicate in range(duplicate_count):
                    scalar_batch = max(
                        scalar_batch,
                        _normalized_max(
                            reference,
                            _values(batch[(repetition, q_id, duplicate)]),
                            sigmas,
                        ),
                    )

    plateaus: dict[str, Any] = {}
    for name, pair in acceptance["plateau_pairs"].items():
        left, right = map(str, pair)
        maximum = math.inf
        if scalar_complete:
            maximum = max(
                _normalized_max(
                    _values(scalar[(left, q_id, 0)]),
                    _values(scalar[(right, q_id, 0)]),
                    sigmas,
                )
                for q_id in q_ids
            )
        plateaus[str(name)] = {
            "case_ids": [left, right],
            "maximum_difference_observation_sigma": (maximum if math.isfinite(maximum) else None),
            "passed": (
                math.isfinite(maximum)
                and maximum <= float(acceptance["maximum_plateau_difference_observation_sigma"])
            ),
        }

    responses: dict[str, Any] = {}
    response_pass = scalar_complete
    if scalar_complete:
        central = float(scalar[(batch_case, "q0", 0)]["outputs"]["DoH"])
        for reaction in protocol["q_contract"]["canonical_order"]:
            minus = float(scalar[(batch_case, f"{reaction}_m1", 0)]["outputs"]["DoH"])
            plus = float(scalar[(batch_case, f"{reaction}_p1", 0)]["outputs"]["DoH"])
            straddles = min(minus, plus) <= central <= max(minus, plus)
            nonzero = minus != central and plus != central and minus != plus
            passed = straddles and nonzero
            responses[str(reaction)] = {
                "central": central,
                "minus_one": minus,
                "plus_one": plus,
                "minus_shift": minus - central,
                "plus_shift": plus - central,
                "straddles_central": straddles,
                "nonzero_response": nonzero,
                "passed": passed,
            }
            response_pass &= passed

    checks = {
        "expected_scalar_rows": len(scalar_rows) == int(acceptance["expected_scalar_rows"]),
        "expected_batch_rows": len(batch_rows) == int(acceptance["expected_batch_rows"]),
        "scalar_grid_complete": scalar_complete,
        "batch_grid_complete": batch_complete,
        "zero_structured_failures": failures == 0,
        "row_status_ok": row_status_ok,
        "finite_outputs": finite_outputs,
        "positive_proton_denominator": positive_protons,
        "zero_scalar_repeat_drift": scalar_repeat == 0.0,
        "zero_batch_repeat_drift": batch_repeat == 0.0,
        "scalar_batch_budget": (
            math.isfinite(scalar_batch)
            and scalar_batch
            <= float(acceptance["maximum_scalar_batch_difference_observation_sigma"])
        ),
        "all_plateaus": all(value["passed"] for value in plateaus.values()),
        "D_over_H_plus_minus_responses": response_pass,
    }
    passed = all(checks.values())
    return {
        "checks": checks,
        "maximum_batch_repeat_drift": (batch_repeat if math.isfinite(batch_repeat) else None),
        "maximum_scalar_batch_difference_observation_sigma": (
            scalar_batch if math.isfinite(scalar_batch) else None
        ),
        "maximum_scalar_repeat_drift": (scalar_repeat if math.isfinite(scalar_repeat) else None),
        "passed": passed,
        "plateaus": plateaus,
        "response_checks": responses,
        "status": "accepted" if passed else "not_accepted",
    }


def validate(artifact_path: Path, config_path: Path) -> dict[str, Any]:
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    stored_digest = artifact.pop("evidence_sha256")
    if digest_json(artifact) != stored_digest:
        raise ValueError("artifact evidence digest mismatch")
    artifact["evidence_sha256"] = stored_digest
    if (
        artifact["schema_version"] != 1
        or artifact["artifact_id"] != ARTIFACT_ID
        or artifact["reproduction_id"] != ARTIFACT_ID
        or artifact["task_id"] != "UQ0-NATIVE-UQ-REPRO"
        or artifact["status"] not in {"accepted_C0_calibration", "complete_not_accepted"}
    ):
        raise ValueError("artifact identity/status drift")
    if sha256(config_path) != EXPECTED_CONFIG_SHA256:
        raise ValueError("frozen protocol hash drift")
    protocol = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if protocol["claim_boundary"] != artifact["claim_boundary"]:
        raise ValueError("claim-boundary drift")
    boundary = artifact["claim_boundary"]
    if (
        boundary["claim_level"] != "C0"
        or boundary["project_scientific_prior_selected"] is not False
        or boundary["ETR25_actual_posterior_reconstructed"] is not False
        or boundary["production_adapter_unlocked"] is not False
        or boundary["gradients_or_HMC_accepted"] is not False
        or boundary["scientific_signoff_provided"] is not False
        or boundary["novelty_claim_allowed"] is not False
    ):
        raise ValueError("artifact overclaims LINX native-q evidence")

    root = artifact_path.parent
    required = {
        "failures.jsonl",
        "resource_report.json",
        "results.json",
        "run_manifest.json",
        "timings.jsonl",
    }
    if set(artifact["companion_sha256"]) != required:
        raise ValueError("companion file set drift")
    for name in required:
        path = root / name
        if not path.is_file() or sha256(path) != artifact["companion_sha256"][name]:
            raise ValueError(f"companion evidence drift: {name}")
    if (root / "failures.jsonl").read_text(encoding="utf-8") != "":
        raise ValueError("structured failure ledger is not empty")

    manifest = json.loads((root / "run_manifest.json").read_text(encoding="utf-8"))
    if (
        manifest["schema_version"] != 1
        or manifest["artifact_id"] != ARTIFACT_ID
        or manifest["task_id"] != "UQ0-NATIVE-UQ-REPRO"
        or manifest["status"] != "complete"
        or manifest["source_revision"] != EXPECTED_REVISION
        or manifest["source_tracked_tree_clean"] is not True
        or manifest["config_sha256"] != EXPECTED_CONFIG_SHA256
        or manifest["mapping_artifact_sha256"] != EXPECTED_MAPPING_SHA256
        or manifest["parameter_schema_sha256"] != EXPECTED_PARAMETER_SHA256
        or manifest["observation_config_sha256"] != EXPECTED_OBSERVATION_SHA256
        or manifest["environment_lock_sha256"] != EXPECTED_LOCK_SHA256
        or manifest["environment"]["jax"] != "0.4.28"
        or manifest["environment"]["jaxlib"] != "0.4.28"
        or manifest["environment"]["backend"] != "cpu"
        or manifest["environment"]["x64"] is not True
        or manifest["background_reused_across_q_draws"] is not True
        or manifest["parameters"] != protocol["parameter_set"]["values"]
    ):
        raise ValueError("run manifest provenance/environment drift")
    if artifact["scientific_scope"] != (
        "LINX native scalar-envelope abundance calibration at one frozen "
        "standard-BBN point; not a selected project prior or posterior"
    ):
        raise ValueError("artifact scientific-scope drift")

    results = json.loads((root / "results.json").read_text(encoding="utf-8"))
    if results["schema_version"] != 1:
        raise ValueError("results schema drift")
    recomputed = recompute_decision(protocol, results)
    if recomputed != results["decision"]:
        raise ValueError("stored results decision differs from recomputation")
    if recomputed != artifact["decision"]:
        raise ValueError("artifact decision differs from recomputation")
    expected_status = "accepted_C0_calibration" if recomputed["passed"] else "complete_not_accepted"
    if artifact["status"] != expected_status:
        raise ValueError("artifact status differs from recomputed acceptance")

    timings = [
        json.loads(line)
        for line in (root / "timings.jsonl").read_text(encoding="utf-8").splitlines()
        if line
    ]
    expected_timing_rows = (
        int(protocol["acceptance"]["expected_scalar_rows"])
        + int(protocol["execution"]["heterogeneous_batch"]["warm_repetitions"])
        + 1
    )
    scalar_timing_keys = {
        (str(row["case_id"]), str(row["q_id"]), int(row["repetition"]))
        for row in timings
        if row.get("kind") == "scalar"
    }
    expected_scalar_timing_keys = {
        (str(case["id"]), str(q["id"]), repetition)
        for case in protocol["numerical_cases"]
        for q in protocol["q_contract"]["vectors"]
        for repetition in range(int(protocol["execution"]["scalar_repetitions_per_case_q"]))
    }
    batch_timing_repetitions = {
        int(row["repetition"]) for row in timings if row.get("kind") == "warm_heterogeneous_batch"
    }
    expected_batch_timing_repetitions = set(
        range(int(protocol["execution"]["heterogeneous_batch"]["warm_repetitions"]))
    )
    cold_batch_timings = [
        row for row in timings if row.get("kind") == "cold_heterogeneous_batch_compile_and_solve"
    ]
    if (
        len(timings) != expected_timing_rows
        or scalar_timing_keys != expected_scalar_timing_keys
        or batch_timing_repetitions != expected_batch_timing_repetitions
        or len(cold_batch_timings) != 1
        or any(row.get("status") != "ok" for row in timings)
        or any(
            not math.isfinite(float(row["elapsed_seconds"])) or float(row["elapsed_seconds"]) < 0.0
            for row in timings
        )
    ):
        raise ValueError("timing ledger is incomplete or invalid")
    resource_report = json.loads((root / "resource_report.json").read_text(encoding="utf-8"))
    if (
        resource_report["schema_version"] != 1
        or resource_report["gpu_hours"] != 0.0
        or not isinstance(resource_report["max_rss_bytes"], int)
        or resource_report["max_rss_bytes"] < 0
        or any(
            not math.isfinite(float(resource_report[key])) or float(resource_report[key]) < 0.0
            for key in (
                "cpu_core_hours",
                "cpu_seconds",
                "estimated_cost_cny",
                "wall_seconds",
                "worker_hours",
            )
        )
    ):
        raise ValueError("resource report is invalid")
    return {
        "accepted": bool(recomputed["passed"]),
        "artifact_id": ARTIFACT_ID,
        "batch_rows": len(results["batch_rows"]),
        "claim_level": "C0",
        "decision": recomputed,
        "evidence_sha256": stored_digest,
        "native_UQ_task_progress_eligible": bool(recomputed["passed"]),
        "scalar_rows": len(results["scalar_rows"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact", type=Path)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/benchmarks/linx_native_q_reproduction_v1.yaml"),
    )
    args = parser.parse_args()
    print(json.dumps(validate(args.artifact, args.config), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
