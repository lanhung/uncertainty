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
    from scripts.validate_R0_correlation_sampler_audit import (
        validate as validate_correlation_sampler,
    )
    from scripts.validate_linx_R0_mapping_regression import (
        validate as validate_linx_mapping,
    )
    from scripts.validate_primat_R0_reverse_regression import (
        validate as validate_primat_reverse,
    )
    from scripts.validate_prymordial_R0_mapping_regression import (
        validate as validate_prymordial_mapping,
    )
except ModuleNotFoundError:  # Direct ``python scripts/<name>.py`` execution.
    from validate_R0_correlation_sampler_audit import (
        validate as validate_correlation_sampler,
    )
    from validate_linx_R0_mapping_regression import (
        validate as validate_linx_mapping,
    )
    from validate_primat_R0_reverse_regression import (
        validate as validate_primat_reverse,
    )
    from validate_prymordial_R0_mapping_regression import (
        validate as validate_prymordial_mapping,
    )


REACTIONS = {"dp_gamma_he3", "dd_n_he3", "dd_p_t"}
ORDER = ["dp_gamma_he3", "dd_n_he3", "dd_p_t"]
EXPECTED_INPUTS = {
    "ETR25_public_tables": {
        "path": "artifacts/priors/ETR25-R0-TABLES-v1/package.json",
        "sha256": "f9f7436378fe8d0985d03ca5e5b48012820948c6a391081438939b63c58df7ba",
    },
    "ETR25_rate_pdf_audit": {
        "path": "artifacts/priors/ETR25-R0-RATE-PDF-AUDIT-v1/audit.json",
        "sha256": "33adba011bc0eddeee6f31b8b43a873cdae30f15c6d1e92aa50fdeafeea9af20",
    },
    "legacy_solver_envelope": {
        "path": "artifacts/priors/NUCLEAR-STAGE0-R0-LINX-KEY-RECOMMENDED-v1/package.json",
        "sha256": "aacca2ad92c2132a67995801d091d9b642f3616cf7cf70b2a54a6e1d4348c745",
    },
}


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

    if registry.get("inputs") != EXPECTED_INPUTS:
        raise ValueError("candidate input registry schema or provenance drift")
    for input_id, input_record in EXPECTED_INPUTS.items():
        input_path = resolve_record_path(repository_root, input_record["path"])
        if sha256(input_path) != input_record["sha256"]:
            raise ValueError(f"candidate input SHA256 mismatch: {input_id}")

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
    if (
        sha256(guard_path)
        != reverse_artifact["project_UpdateNuclearRates_wrapper_guard_regression"]["guard_sha256"]
    ):
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
    if not frozen_reverse["R0_reverse_cap_not_detected_on_actual_LT_probe_points_within_tolerance"]:
        raise ValueError("PRIMAT actual-LT probe cap result is hidden")
    if frozen_reverse["R0_reverse_cap_not_detected_over_full_diagnostic_grid_within_tolerance"]:
        raise ValueError("PRIMAT above-LT cap boundary is hidden")
    if frozen_reverse["actual_solver_temperature_trajectory_evaluated"]:
        raise ValueError("PRIMAT solver-trajectory coverage is overstated")
    if not frozen_reverse["project_wrapper_guard_passed"]:
        raise ValueError("PRIMAT MT/LT wrapper guard result is hidden")
    if reverse_summary["cache_guard_required"] is not True:
        raise ValueError("PRIMAT cache guard requirement is hidden")

    linx_record = registry["candidate_artifacts"]["LINX_mapping_regression"]
    linx_path = resolve_record_path(repository_root, linx_record["path"])
    if sha256(linx_path) != linx_record["sha256"]:
        raise ValueError("LINX mapping regression SHA256 mismatch")
    linx_summary = validate_linx_mapping(linx_path)
    if linx_summary != {
        "reactions": 3,
        "unique_q_indices": 3,
        "rate_rows": 4485,
        "reverse_ratio_defined_rows": 2430,
        "reverse_underflow_excluded_rows": 2055,
        "out_of_grid_rows": 30,
        "consecutive_draw_rows": 96,
        "consecutive_draw_reverse_underflow_excluded_rows": 24,
        "acceptance_passes": True,
    }:
        raise ValueError("LINX mapping regression summary drift")

    prymordial_record = registry["candidate_artifacts"]["PRyMordial_mapping_regression"]
    prymordial_path = resolve_record_path(repository_root, prymordial_record["path"])
    if sha256(prymordial_path) != prymordial_record["sha256"]:
        raise ValueError("PRyMordial mapping regression SHA256 mismatch")
    prymordial_summary = validate_prymordial_mapping(prymordial_path)
    if (
        prymordial_summary["reaction_count"] != 3
        or prymordial_summary["q_count"] != 5
        or prymordial_summary["forward_rows"] != 14985
        or prymordial_summary["reverse_rows_defined"] != 8145
        or prymordial_summary["reverse_rows_excluded_zero_or_subnormal"] != 6840
        or prymordial_summary["all_three_mappings_unique"] is not True
        or prymordial_summary["duplicate_shift_guard_passed"] is not True
        or prymordial_summary["sequential_draw_contamination_observed"] is not False
    ):
        raise ValueError("PRyMordial mapping regression summary drift")

    sampler_record = registry["candidate_artifacts"]["correlation_sampler_audit"]
    sampler_path = resolve_record_path(repository_root, sampler_record["path"])
    if sha256(sampler_path) != sampler_record["sha256"]:
        raise ValueError("correlation sampler audit SHA256 mismatch")
    sampler_summary = validate_correlation_sampler(sampler_path, repository_root)
    if (
        sampler_summary["model_records"] != 35
        or sampler_summary["unique_matrix_sha256"] != 34
        or sampler_summary["all_model_checks_passed"] is not True
        or sampler_summary["fixed_seed_replay_passed_models"] != 35
        or sampler_summary["nearest_PSD_projection_used_models"] != 0
    ):
        raise ValueError("correlation sampler audit summary drift")

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
    registry_completion = registry["completion_boundary"]
    for field in (
        "PRIMAT_reverse_regression_passed",
        "PRIMAT_cache_guard_implemented",
        "LINX_mapping_regression_passed",
        "PRyMordial_mapping_regression_passed",
        "correlation_sampler_audit_passed",
    ):
        if registry_completion[field] is not True:
            raise ValueError(f"completed numerical audit is not recorded: {field}")
    for field in (
        "actual_posterior_or_original_nuclear_model_available",
        "PRIMAT_solver_trajectory_cap_regression_passed",
        "PRIMAT_ETR25_curve_injection_regression_passed",
        "task_done_allowed",
        "production_adapter_unlocked",
    ):
        if registry_completion[field] is not False:
            raise ValueError(f"candidate registry manufactures completion: {field}")
    if (
        registry_completion["accepted_scientific_prior_reactions"] != 0
        or registry_completion["coherent_actual_draw_gate_closed"] is not True
    ):
        raise ValueError("candidate registry manufactures scientific acceptance")
    if {
        registry_completion["A03_nuclear_data_signoff"],
        registry_completion["A00_scientific_signoff"],
        registry_completion["A09_independent_validation"],
    } != {"pending"}:
        raise ValueError("candidate registry manufactures sign-offs")
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
        "numerical_mapping_regressions_passed": 3,
        "correlation_sampler_models_passed": sampler_summary["model_records"],
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
