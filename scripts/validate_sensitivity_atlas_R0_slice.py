#!/usr/bin/env python3
"""Fail-closed validator for the public sensitivity-atlas R0 slice."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any


EXPECTED_REACTIONS = {"dpHe3g", "ddHe3n", "ddtp"}
EXPECTED_REVISION = "d3ea1838d9450673698f07b7c6b8971efb87d0fd"
EXPECTED_PRYM_REVISION = "725d8a8db3ad5ea2630580d825c9d0d69ed76533"
EXPECTED_TABLE_SHA256 = "bf7bd5bcb1753a7e805837e18460b85d3af06fa4fdaf0d5f96b4eee7bff0f035"


def digest_json(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def validate(path: Path) -> dict[str, Any]:
    artifact = json.loads(path.read_text(encoding="utf-8"))
    stored = artifact.pop("evidence_sha256")
    if digest_json(artifact) != stored:
        raise ValueError("artifact evidence digest mismatch")
    artifact["evidence_sha256"] = stored
    if (
        artifact["schema_version"] != 1
        or artifact["artifact_id"] != "SENSITIVITY-ATLAS-R0-SLICE-v1"
        or artifact["task_id"] != "UQ0-NATIVE-UQ-REPRO"
    ):
        raise ValueError("artifact identity drift")
    if artifact["status"] not in {
        "accepted_independent_public_calibration_reproduction",
        "failed_independent_public_calibration_reproduction",
    }:
        raise ValueError("artifact status drift")
    scope = artifact["scientific_scope"]
    if (
        scope["claim_level"] != "C0_public_calibration_reproduction_only"
        or scope["accepted_scientific_prior"] is not False
        or scope["production_authorized"] is not False
        or scope["novelty_claim"] is not False
    ):
        raise ValueError("scientific boundary overclaim")
    source = artifact["source"]
    if (
        source["atlas_revision"] != EXPECTED_REVISION
        or source["atlas_table_sha256"] != EXPECTED_TABLE_SHA256
        or source["prymordial_revision"] != EXPECTED_PRYM_REVISION
        or source["atlas_generator_revision_available"] is not False
    ):
        raise ValueError("source provenance drift")
    recomputed_failures: list[str] = []
    if artifact["attempted_solve_count"] != 10:
        recomputed_failures.append("incomplete_solve_accounting")
    if artifact["failure_count"] != 0 or artifact["failures"] != []:
        recomputed_failures.append("structured_solver_failures_present")
    if not math.isfinite(float(artifact["runtime_seconds_total"])):
        raise ValueError("runtime accounting is not finite")
    maximum_repeat = float(artifact["maximum_repeat_relative_drift"])
    contract = artifact["acceptance_contract"]
    if maximum_repeat > float(contract["maximum_repeat_relative_drift"]):
        recomputed_failures.append("central_repeat_drift_exceeds_contract")
    comparisons = artifact["comparisons"]
    if set(comparisons) != EXPECTED_REACTIONS:
        raise ValueError("R0 reaction set drift")

    maximum_central = 0.0
    maximum_derivative_relative = 0.0
    for reaction, result in comparisons.items():
        for abundance in ("Yp", "DH", "Li7H"):
            minus = float(result["minus_one_sigma"][abundance])
            central = float(result["central"][abundance])
            plus = float(result["plus_one_sigma"][abundance])
            derivative = float(result["centered_derivative_per_q"][abundance])
            reference_central = float(result["published_central"][abundance])
            reference_derivative = float(result["published_derivative_per_q"][abundance])
            if not all(math.isfinite(value) and value > 0 for value in (minus, central, plus)):
                raise ValueError("non-finite or non-positive abundance output")
            central_difference = abs(central - reference_central)
            maximum_central = max(maximum_central, central_difference)
            if central_difference > float(
                contract["maximum_central_absolute_difference"][abundance]
            ):
                recomputed_failures.append(f"central_reference_mismatch:{reaction}:{abundance}")
            absolute_difference = abs(derivative - reference_derivative)
            relative_difference = absolute_difference / max(abs(reference_derivative), 1.0e-300)
            maximum_derivative_relative = max(maximum_derivative_relative, relative_difference)
            floor = float(contract["derivative_absolute_floor"][abundance])
            relative_limit = float(contract["maximum_derivative_relative_difference"][abundance])
            if absolute_difference > floor and relative_difference > relative_limit:
                recomputed_failures.append(f"derivative_reference_mismatch:{reaction}:{abundance}")
            if (
                contract["require_expected_derivative_sign"]
                and derivative * reference_derivative <= 0
            ):
                recomputed_failures.append(f"derivative_sign_mismatch:{reaction}:{abundance}")

    recomputed_failures = sorted(set(recomputed_failures))
    accepted = not recomputed_failures
    if artifact["acceptance_failures"] != recomputed_failures:
        raise ValueError("recorded acceptance failures do not match recomputation")
    if artifact["acceptance_passes"] is not accepted:
        raise ValueError("recorded acceptance decision does not match recomputation")
    if artifact["native_UQ_task_progress_eligible"] is not accepted:
        raise ValueError("task-progress eligibility does not match acceptance")
    expected_status = (
        "accepted_independent_public_calibration_reproduction"
        if accepted
        else "failed_independent_public_calibration_reproduction"
    )
    if artifact["status"] != expected_status:
        raise ValueError("status does not match acceptance")

    return {
        "accepted": accepted,
        "native_UQ_task_progress_eligible": accepted,
        "acceptance_failures": recomputed_failures,
        "reaction_count": len(comparisons),
        "attempted_solve_count": artifact["attempted_solve_count"],
        "maximum_central_absolute_difference": maximum_central,
        "maximum_derivative_relative_difference": maximum_derivative_relative,
        "maximum_repeat_relative_drift": maximum_repeat,
        "evidence_sha256": stored,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact", type=Path)
    args = parser.parse_args()
    print(json.dumps(validate(args.artifact), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
