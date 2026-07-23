#!/usr/bin/env python3
"""Validate the non-production R0 prior candidate and stress contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import yaml

try:
    from scripts.validate_primat_R0_reverse_regression import (
        validate as validate_primat_reverse,
    )
except ModuleNotFoundError:  # Direct ``python scripts/<name>.py`` execution.
    from validate_primat_R0_reverse_regression import (
        validate as validate_primat_reverse,
    )


REACTIONS = {"dp_gamma_he3", "dd_n_he3", "dd_p_t"}
ORDER = ["dp_gamma_he3", "dd_n_he3", "dd_p_t"]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def payload_sha256(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected a mapping in {path}")
    return payload


def resolve_record_path(repository_root: Path, path: str) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else repository_root / candidate


def determinant(matrix: list[list[float]]) -> float:
    a, b, c = matrix[0]
    _, d, e = matrix[1]
    _, _, f = matrix[2]
    return a * d * f + 2 * b * c * e - a * e * e - d * c * c - f * b * b


def reconstruct_from_cholesky(lower: list[list[float]]) -> list[list[float]]:
    return [[sum(lower[i][k] * lower[j][k] for k in range(3)) for j in range(3)] for i in range(3)]


def validate(
    registry_path: Path,
    stage_path: Path,
    engineering_path: Path,
    repository_root: Path,
) -> dict[str, int]:
    registry = load_yaml(registry_path)
    stage = load_yaml(stage_path)
    engineering = load_yaml(engineering_path)

    if registry.get("schema_version") != 1:
        raise ValueError("unsupported R0 candidate schema")
    if registry.get("candidate_id") != "NUCLEAR-R0-CANDIDATE-v1":
        raise ValueError("unexpected R0 candidate id")
    if registry.get("status") != ("numerical_candidate_ready_scientific_prior_not_selected"):
        raise ValueError("R0 candidate status exceeds its evidence")
    if registry.get("production_use") != "prohibited":
        raise ValueError("R0 candidate must prohibit production")

    comparator_record = registry["candidate_artifacts"]["coherent_comparators"]
    comparator_path = resolve_record_path(repository_root, comparator_record["path"])
    if sha256(comparator_path) != comparator_record["sha256"]:
        raise ValueError("coherent comparator SHA256 mismatch")
    comparators = json.loads(comparator_path.read_text(encoding="utf-8"))
    if set(comparators["reactions"]) != REACTIONS:
        raise ValueError("coherent comparator reaction set differs from R0")
    surrogate = comparators["quantile_matched_asymmetric_rank1_surrogate"]
    if surrogate["actual_posterior_reconstruction"] is not False:
        raise ValueError("quantile surrogate cannot claim actual posterior")
    if surrogate["validated_nuclear_input_coherence"] is not False:
        raise ValueError("mathematical coherence is not nuclear-input validation")
    if surrogate["temperature_copula"] != ("imposed_comonotonic_rank_one_not_inferred"):
        raise ValueError("surrogate temperature copula is overstated")
    if comparators["safety"]["scientific_prior_selected"] is not False:
        raise ValueError("comparator package cannot select the scientific prior")
    if comparators["safety"]["production_use"] != "prohibited":
        raise ValueError("comparator package cannot authorize production")

    comparator_rows = 0
    for reaction in comparators["reactions"].values():
        summary = reaction["summary"]
        if summary["rows"] != 60 or summary["strict_L_less_M_less_H_rows"] != 60:
            raise ValueError("quantile surrogate row-shape regression failed")
        if summary["max_abs_relative_quantile_reconstruction_error"] >= 1e-14:
            raise ValueError("quantile surrogate no longer matches public quantiles")
        comparator_rows += summary["rows"]
        for row in reaction["rows"]:
            quantiles = row["source_actual_percentiles"]
            if not quantiles["p16"] < quantiles["p50"] < quantiles["p84"]:
                raise ValueError("quantile order is not strict")
            slopes = row["quantile_matched_asymmetric_rank1_surrogate"]
            if (
                min(
                    slopes["lower_log_slope_per_q"],
                    slopes["upper_log_slope_per_q"],
                )
                <= 0
            ):
                raise ValueError("quantile surrogate slope is not positive")

    contract_record = registry["candidate_artifacts"]["candidate_contract"]
    contract_path = resolve_record_path(repository_root, contract_record["path"])
    if sha256(contract_path) != contract_record["sha256"]:
        raise ValueError("R0 candidate contract SHA256 mismatch")
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    if contract["reaction_order"] != ORDER:
        raise ValueError("R0 correlation order drift")
    if (
        contract["candidate_representations"]["quantile_matched_asymmetric_rank1_surrogate"][
            "production_allowed"
        ]
        is not False
    ):
        raise ValueError("quantile surrogate cannot enter production")

    reverse_record = registry["candidate_artifacts"]["PRIMAT_reverse_regression"]
    reverse_path = resolve_record_path(repository_root, reverse_record["path"])
    if sha256(reverse_path) != reverse_record["sha256"]:
        raise ValueError("PRIMAT reverse regression SHA256 mismatch")
    reverse_summary = validate_primat_reverse(reverse_path)
    reverse_artifact = json.loads(reverse_path.read_text(encoding="utf-8"))
    guard_path = repository_root / "worker/primat_rate_draw.py"
    if sha256(guard_path) != reverse_artifact[
        "project_UpdateNuclearRates_wrapper_guard_regression"
    ]["guard_sha256"]:
        raise ValueError("project PRIMAT wrapper guard SHA256 mismatch")

    reverse = contract["solver_reverse_status"]
    if reverse["LINX"]["same_perturbed_forward_used_by_reverse"] is not True:
        raise ValueError("LINX reverse source contract drift")
    if reverse["PRyMordial"]["same_perturbed_forward_used_by_reverse"] is not True:
        raise ValueError("PRyMordial reverse source contract drift")
    primat = reverse["PRIMAT"]
    if primat["strict_same_draw_detailed_balance_unconditional"] is not False:
        raise ValueError("PRIMAT median-derived reverse cap is hidden")
    if primat["consecutive_draw_cache_regression_required"] is not True:
        raise ValueError("PRIMAT consecutive-draw regression requirement is hidden")
    if primat["consecutive_draw_cache_regression_completed"] is not True:
        raise ValueError("PRIMAT consecutive-draw regression is missing")
    frozen_reverse = primat["reverse_regression"]
    if frozen_reverse["sha256"] != reverse_record["sha256"]:
        raise ValueError("contract and registry disagree on PRIMAT regression")
    if not frozen_reverse[
        "R0_reverse_cap_not_detected_on_actual_LT_probe_points_within_tolerance"
    ]:
        raise ValueError("PRIMAT actual-LT probe cap result is hidden")
    if frozen_reverse[
        "R0_reverse_cap_not_detected_over_full_diagnostic_grid_within_tolerance"
    ]:
        raise ValueError("PRIMAT above-LT cap boundary is hidden")
    if frozen_reverse["actual_solver_temperature_trajectory_evaluated"]:
        raise ValueError("PRIMAT solver-trajectory coverage is overstated")
    if not frozen_reverse["project_wrapper_guard_passed"]:
        raise ValueError("PRIMAT MT/LT wrapper guard result is hidden")
    if reverse_summary["cache_guard_required"] is not True:
        raise ValueError("PRIMAT cache guard requirement is hidden")
    completion = contract["completion_boundary"]
    if completion["PRIMAT_reverse_regression_passed"] is not True:
        raise ValueError("completed PRIMAT reverse regression is not recorded")
    if completion["PRIMAT_cache_guard_implemented"] is not True:
        raise ValueError("PRIMAT cache guard implementation is not recorded")
    if completion["PRIMAT_solver_trajectory_cap_regression_passed"] is not False:
        raise ValueError("PRIMAT solver-trajectory cap gate was manufactured")
    if completion["PRIMAT_ETR25_curve_injection_regression_passed"] is not False:
        raise ValueError("PRIMAT ETR25 injection cap gate was manufactured")
    if completion["accepted_scientific_prior_reactions"] != 0:
        raise ValueError("numerical regression cannot accept the scientific prior")
    if completion["production_adapter_unlocked"] is not False:
        raise ValueError("numerical regression cannot unlock production")
    engineering_primat = engineering["solver_mappings"]["PRIMAT_S8"]
    if engineering_primat["repository"] != "https://github.com/CyrilPitrou/primat":
        raise ValueError("PRIMAT source repository is not canonical")
    if engineering_primat["reverse_uses_same_perturbed_forward_rate"] != (
        "true_before_reverse_cap_or_where_cap_is_inactive"
    ):
        raise ValueError("engineering contract overstates PRIMAT detailed balance")
    if engineering_primat["native_reverse_cap"]["recomputed_by_apply_variations"] is not False:
        raise ValueError("engineering contract hides the PRIMAT cap behavior")

    stress = contract["correlation_stress_suite"]
    matrices = stress["matrices"]
    if stress["model_count"] != 35 or len(matrices) != 35:
        raise ValueError("correlation stress suite must contain 35 model records")
    if stress["unique_matrix_count"] != 34:
        raise ValueError("correlation stress suite unique-matrix count drift")
    if stress["identity_is_scientific_default"] is not False:
        raise ValueError("identity covariance cannot be the scientific default")
    if stress["nearest_PSD_projection_allowed"] is not False:
        raise ValueError("nearest-PSD projection must fail closed")

    matrix_ids: set[str] = set()
    matrix_hashes: set[str] = set()
    for record in matrices:
        matrix = record["ordered_matrix"]
        matrix_id = record["model_id"]
        if matrix_id in matrix_ids:
            raise ValueError("duplicate correlation model id")
        matrix_ids.add(matrix_id)
        if record["matrix_sha256"] != payload_sha256(matrix):
            raise ValueError(f"{matrix_id}: correlation matrix SHA256 mismatch")
        matrix_hashes.add(record["matrix_sha256"])
        if any(
            not math.isclose(matrix[i][j], matrix[j][i], abs_tol=1e-15)
            for i in range(3)
            for j in range(3)
        ):
            raise ValueError(f"{matrix_id}: correlation matrix is not symmetric")
        if any(matrix[i][i] != 1.0 for i in range(3)):
            raise ValueError(f"{matrix_id}: correlation diagonal drift")
        det = determinant(matrix)
        if det <= 0 or not math.isclose(det, record["determinant"], rel_tol=0, abs_tol=1e-14):
            raise ValueError(f"{matrix_id}: invalid determinant")
        reconstructed = reconstruct_from_cholesky(record["Cholesky_lower"])
        if any(
            not math.isclose(
                reconstructed[i][j],
                matrix[i][j],
                rel_tol=0,
                abs_tol=1e-14,
            )
            for i in range(3)
            for j in range(3)
        ):
            raise ValueError(f"{matrix_id}: Cholesky reconstruction failed")
        if record["nearest_PSD_projection_allowed"] is not False:
            raise ValueError(f"{matrix_id}: silent PSD projection is allowed")
    if len(matrix_hashes) != 34:
        raise ValueError("unexpected correlation matrix duplication")
    duplicate = stress["intentional_duplicate_anchor"]["model_ids"]
    by_id = {record["model_id"]: record for record in matrices}
    if by_id[duplicate[0]]["matrix_sha256"] != by_id[duplicate[1]]["matrix_sha256"]:
        raise ValueError("declared identity/Vine-center duplicate is not identical")

    completion = contract["completion_boundary"]
    if completion["numerical_candidate_reactions"] != 3:
        raise ValueError("numerical candidate reaction count drift")
    if completion["accepted_scientific_prior_reactions"] != 0:
        raise ValueError("candidate package manufactures scientific acceptance")
    if completion["task_done_allowed"] is not False:
        raise ValueError("candidate package cannot complete UQ0-R0-RATE-PRIOR")
    if completion["production_adapter_unlocked"] is not False:
        raise ValueError("candidate package cannot unlock the adapter")
    if {
        completion["A03_nuclear_data_signoff"],
        completion["A00_scientific_signoff"],
        completion["A09_independent_validation"],
    } != {"pending"}:
        raise ValueError("candidate package manufactures sign-offs")

    stage_candidate = stage["nuisance_contract"]["numerical_candidate"]
    if stage_candidate["registry"] != str(registry_path.relative_to(repository_root)):
        raise ValueError("Stage-R0 does not bind the candidate registry")
    if stage_candidate["production_use"] != "prohibited":
        raise ValueError("Stage-R0 candidate cannot authorize production")
    if any(item["production_enabled"] is not False for item in stage["reactions"]):
        raise ValueError("Stage-R0 production must remain disabled")

    return {
        "reactions": len(REACTIONS),
        "comparator_rows": comparator_rows,
        "correlation_models": len(matrices),
        "unique_correlation_matrices": len(matrix_hashes),
        "accepted_scientific_prior_reactions": (completion["accepted_scientific_prior_reactions"]),
        "production_enabled_reactions": sum(
            bool(item["production_enabled"]) for item in stage["reactions"]
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument("--engineering-prior", type=Path, required=True)
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    summary = validate(
        args.registry.resolve(),
        args.stage.resolve(),
        args.engineering_prior.resolve(),
        args.repository_root.resolve(),
    )
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
