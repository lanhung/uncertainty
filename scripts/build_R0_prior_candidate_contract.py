#!/usr/bin/env python3
"""Build the non-production R0 prior candidate and correlation-stress contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from itertools import product
from pathlib import Path
from typing import Any


EXPECTED_COMPARATOR_SHA256 = "0634a74a1e1937b8d6b959282f10e21f505514e7449ccbd05b5e639083f2b5dd"
EXPECTED_PRIMAT_REVERSE_SHA256 = (
    "cf665f1d1de758122d47b3cb5c0fb18a073f379aff8abacc440430e98158a6ae"
)
ORDER = ["dp_gamma_he3", "dd_n_he3", "dd_p_t"]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def payload_sha256(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def determinant(matrix: list[list[float]]) -> float:
    a, b, c = matrix[0]
    _, d, e = matrix[1]
    _, _, f = matrix[2]
    return a * d * f + 2 * b * c * e - a * e * e - d * c * c - f * b * b


def cholesky(matrix: list[list[float]]) -> list[list[float]]:
    lower = [[0.0] * 3 for _ in range(3)]
    for row in range(3):
        for column in range(row + 1):
            residual = matrix[row][column] - sum(
                lower[row][k] * lower[column][k] for k in range(column)
            )
            if row == column:
                if residual <= 0:
                    raise ValueError("correlation matrix is not positive definite")
                lower[row][column] = math.sqrt(residual)
            else:
                lower[row][column] = residual / lower[column][column]
    return lower


def matrix_record(
    model_id: str,
    family: str,
    matrix: list[list[float]],
    parameters: dict[str, float],
) -> dict[str, Any]:
    if any(len(row) != 3 for row in matrix) or len(matrix) != 3:
        raise ValueError(f"{model_id}: expected a 3x3 matrix")
    if any(matrix[i][j] != matrix[j][i] for i in range(3) for j in range(3)):
        raise ValueError(f"{model_id}: matrix is not symmetric")
    if any(matrix[i][i] != 1.0 for i in range(3)):
        raise ValueError(f"{model_id}: diagonal differs from one")
    if any(not math.isfinite(value) or abs(value) > 1 for row in matrix for value in row):
        raise ValueError(f"{model_id}: invalid correlation coefficient")
    det = determinant(matrix)
    if det <= 0:
        raise ValueError(f"{model_id}: matrix determinant is not positive")
    lower = cholesky(matrix)
    return {
        "model_id": model_id,
        "family": family,
        "parameters": parameters,
        "ordered_matrix": matrix,
        "matrix_sha256": payload_sha256(matrix),
        "determinant": det,
        "factorization": "Cholesky_lower",
        "Cholesky_lower": lower,
        "nearest_PSD_projection_allowed": False,
    }


def correlation_suite() -> list[dict[str, Any]]:
    records = [
        matrix_record(
            "I3",
            "engineering_identity_comparator",
            [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
            {},
        )
    ]
    for rho in (-0.9, -0.5, 0.5, 0.9):
        records.append(
            matrix_record(
                f"DD_{rho:+.2f}",
                "dd_pair_only",
                [[1.0, 0.0, 0.0], [0.0, 1.0, rho], [0.0, rho, 1.0]],
                {"rho_dd": rho},
            )
        )
    for rho in (0.25, 0.5, 0.9):
        records.append(
            matrix_record(
                f"COMMON_{rho:+.2f}",
                "positive_equicorrelation",
                [[1.0, rho, rho], [rho, 1.0, rho], [rho, rho, 1.0]],
                {"rho": rho},
            )
        )
    grid = (-0.75, 0.0, 0.75)
    for u, v, w in product(grid, repeat=3):
        rho_12 = u
        rho_13 = v
        rho_23 = u * v + w * math.sqrt((1 - u * u) * (1 - v * v))
        records.append(
            matrix_record(
                f"VINE_u{u:+.2f}_v{v:+.2f}_w{w:+.2f}",
                "symmetric_preregistered_partial_correlation_grid",
                [
                    [1.0, rho_12, rho_13],
                    [rho_12, 1.0, rho_23],
                    [rho_13, rho_23, 1.0],
                ],
                {"u": u, "v": v, "w": w},
            )
        )
    return records


def build(comparator_path: Path, primat_reverse_path: Path) -> dict[str, Any]:
    actual_sha256 = sha256(comparator_path)
    if actual_sha256 != EXPECTED_COMPARATOR_SHA256:
        raise ValueError(
            f"comparator SHA256 mismatch: {actual_sha256} != {EXPECTED_COMPARATOR_SHA256}"
        )
    comparator = json.loads(comparator_path.read_text(encoding="utf-8"))
    if set(comparator["reactions"]) != set(ORDER):
        raise ValueError("comparator package reaction order is incomplete")
    reverse_sha256 = sha256(primat_reverse_path)
    if reverse_sha256 != EXPECTED_PRIMAT_REVERSE_SHA256:
        raise ValueError(
            "PRIMAT reverse regression SHA256 mismatch: "
            f"{reverse_sha256} != {EXPECTED_PRIMAT_REVERSE_SHA256}"
        )
    reverse_regression = json.loads(primat_reverse_path.read_text(encoding="utf-8"))
    reverse_acceptance = reverse_regression["acceptance"]
    if not (
        reverse_acceptance["unclamped_reverse_detailed_balance_passed"]
        and reverse_acceptance["unclamped_log_shift_identity_passed"]
        and reverse_acceptance[
            "R0_reverse_cap_not_detected_on_actual_LT_probe_points_within_tolerance"
        ]
        and reverse_acceptance["upstream_cache_invalidation_required"]
        and reverse_acceptance["project_wrapper_guard_passed"]
    ):
        raise ValueError("PRIMAT reverse/cache regression does not satisfy the contract")
    matrices = correlation_suite()
    unique_matrix_count = len({record["matrix_sha256"] for record in matrices})
    return {
        "schema_version": 1,
        "contract_id": "R0-PRIOR-CANDIDATE-CONTRACT-v1",
        "task_id": "UQ0-R0-RATE-PRIOR",
        "status": (
            "numerical_candidate_ready_actual_posterior_and_signoffs_pending"
        ),
        "reaction_order": ORDER,
        "candidate_representations": {
            "actual_pointwise_percentile_envelope": {
                "available": True,
                "coherent_sampling_available": False,
                "role": "descriptive_source_product_only",
            },
            "quantile_matched_asymmetric_rank1_surrogate": {
                "package": str(comparator_path),
                "package_sha256": actual_sha256,
                "role": "asymmetric_comparator_only",
                "actual_posterior_reconstruction": False,
                "production_allowed": False,
            },
            "ETR25_scalar_lognormal_proxy": {
                "package": str(comparator_path),
                "package_sha256": actual_sha256,
                "role": "source_convention_scalar_comparator_only",
                "actual_posterior_reconstruction": False,
                "production_allowed": False,
            },
            "legacy_solver_envelope": {
                "package": (
                    "artifacts/priors/NUCLEAR-STAGE0-R0-LINX-KEY-RECOMMENDED-v1/package.json"
                ),
                "role": "native_reproduction_and_interface_calibration_only",
                "production_allowed": False,
            },
        },
        "reverse_rate_contract": {
            "canonical_equation": (
                "reverse_i(T,draw)=K_i(T)*forward_i(T,draw), K_i=alpha_i*T9^beta_i*exp(gamma_i/T9)"
            ),
            "requirements": [
                "same_nuclear_input_draw_id_and_same_z_for_forward_and_reverse",
                "perturb_forward_knots_then_interpolate_then_apply_detailed_balance",
                "freeze_alpha_beta_gamma_masses_partitions_and_QED_settings",
                "do_not_duplicate_identical_reactant_symmetry_factor",
                "derive_any_floor_or_cap_from_the_same_perturbed_forward_draw",
                "choose_exactly_one_rate_representation_per_run",
                "reject_out_of_table_domain_before_solver_call",
            ],
            "FP64_regression": {
                "q_values": [-3.0, -1.0, 0.0, 1.0, 3.0],
                "evaluation_points": [
                    "28_registered_ETR25_primary_knots",
                    "27_registered_ETR25_primary_geometric_midpoints",
                    "510_PRIMAT_native_LT_grid_knots",
                    "509_PRIMAT_native_LT_grid_geometric_midpoints",
                    "both_LT_boundary_points",
                ],
                "actual_solver_temperature_trajectory_evaluated": False,
                "ratio_identity": "reverse/(K*forward)=1",
                "shift_identity": ("ln(reverse(z)/reverse(0))-ln(forward(z)/forward(0))=0"),
                "absolute_tolerance": 1e-10,
                "explicit_underflow_or_zero_floor_exclusions_only": True,
            },
        },
        "solver_reverse_status": {
            "LINX": {
                "revision": "ec2e9d2ca455e8204137e884da29f5dd13a638fa",
                "same_perturbed_forward_used_by_reverse": True,
                "source_files": {
                    "linx/reactions.py": (
                        "5ebdb9c86978c19213d72adb3371e649ce1adffc3c8fa395dd39d0410ccbc0ee"
                    ),
                    "linx/nuclear.py": (
                        "b969043f545cfeddf41d4c3c9c376f9dfb12a52ba67cd2472f0f324f2ee126b8"
                    ),
                },
            },
            "PRyMordial": {
                "revision": "725d8a8db3ad5ea2630580d825c9d0d69ed76533",
                "same_perturbed_forward_used_by_reverse": True,
                "NP_nuclear_flag_required": False,
                "source_files": {
                    "PRyM/PRyM_nuclear_net12.py": (
                        "85ffa209d50cf60d1cc5ddad8288ba0237ac39f435c387780a58973327f060d1"
                    ),
                    "PRyM/PRyM_init.py": (
                        "7b52cdd4cf7a7c39082d6cdf4a2e4f3b67458dc20d6ff9f07c2b488ef1819e2f"
                    ),
                },
            },
            "PRIMAT": {
                "revision": "21ff8f39fa18e3937e9fdf386cfa982361bfdfce",
                "same_perturbed_forward_used_before_cap": True,
                "native_reverse_cap": (
                    "load_time_median_QED_forward_not_recomputed_by_apply_variations"
                ),
                "strict_same_draw_detailed_balance_unconditional": False,
                "production_remediation": (
                    "project MT/LT cache guard after every apply_variations is "
                    "implemented; emitted solver-trajectory and ETR25 curve-injection "
                    "cap regressions remain mandatory before production"
                ),
                "consecutive_draw_cache_regression_required": True,
                "consecutive_draw_cache_regression_completed": True,
                "project_cache_guard": "worker/primat_rate_draw.py",
                "reverse_regression": {
                    "path": str(primat_reverse_path),
                    "sha256": reverse_sha256,
                    "artifact_id": reverse_regression["artifact_id"],
                    "unclamped_reverse_detailed_balance_passed": True,
                    "unclamped_log_shift_identity_passed": True,
                    "R0_reverse_cap_not_detected_on_actual_LT_probe_points_within_tolerance": (
                        True
                    ),
                    "R0_reverse_cap_not_detected_over_full_diagnostic_grid_within_tolerance": (
                        False
                    ),
                    "actual_solver_temperature_trajectory_evaluated": False,
                    "rate_draw_model": "PRIMAT_native_p_and_expsigma_not_ETR25_injection",
                    "reverse_cap_active_within_tolerance_rows": reverse_acceptance[
                        "reverse_cap_active_within_tolerance_rows"
                    ],
                    "reverse_cap_active_actual_LT_probe_rows": reverse_acceptance[
                        "reverse_cap_active_actual_LT_probe_rows"
                    ],
                    "upstream_cache_invalidation_required": True,
                    "project_wrapper_guard_passed": True,
                },
                "source_files": {
                    "primat/network_data.py": (
                        "96a771b2e6c23b9d17500740f8ffc9bfecb41d89c23904de4f1a356ca677e1ec"
                    ),
                    "primat/data/csv/detailed_balance.csv": (
                        "a1dc17ebf9f61a1f978e6b72dfb5bc80b592287ce55507110f962d6be581e4df"
                    ),
                    "primat/config.py": (
                        "ec3f905975f98d90f976456e2d2827b93e933ba92b9fef16d5f6445421fd2ce2"
                    ),
                },
            },
        },
        "matched_engine_boundary": {
            "native_inverse_coefficients_byte_identical": False,
            "example_dp_gamma_alpha": {
                "LINX": 1.6335102e10,
                "PRyMordial": 1.6335e10,
                "PRIMAT": 1.6335106e10,
            },
            "native_runs_role": "pipeline_comparison",
            "engine_discrepancy_claim_allowed": False,
            "required_for_matched_engine_comparison": (
                "select_and_inject_one_canonical_coefficient_source"
            ),
        },
        "correlation_stress_suite": {
            "status": "preregistered_scalar_Gaussian_copula_stress_not_inferred",
            "model_count": len(matrices),
            "unique_matrix_count": unique_matrix_count,
            "intentional_duplicate_anchor": {
                "model_ids": ["I3", "VINE_u+0.00_v+0.00_w+0.00"],
                "reason": (
                    "retain_the_identity_family_anchor_and_the_predeclared_"
                    "center_of_the_complete_3x3x3_vine_grid"
                ),
            },
            "identity_is_scientific_default": False,
            "nearest_PSD_projection_allowed": False,
            "matrix_acceptance": [
                "symmetric",
                "unit_diagonal",
                "all_finite",
                "absolute_correlations_at_most_one",
                "strictly_positive_determinant",
                "Cholesky_factorization_succeeds",
            ],
            "run_manifest_fields": [
                "correlation_model_id",
                "ordered_matrix",
                "matrix_sha256",
                "factorization_method",
                "seed",
                "latent_epsilon",
                "realized_z",
                "rate_representation",
            ],
            "matrices": matrices,
        },
        "double_counting_prohibitions": [
            "independent_forward_and_reverse_z_draws",
            "PRIMAT_simultaneous_p_and_nonzero_delta",
            "PRyMordial_simultaneous_p_and_NP_delta",
            "external_manifest_plus_solver_native_MC_for_same_rates",
            "external_tau_n_plus_PRIMAT_native_std_tau_n",
            "prebaked_nuclear_QED_plus_PRIMAT_nuclear_QED",
            "ETR25_proxy_sigma_plus_solver_legacy_sigma",
            "duplicate_identical_reactant_symmetry_factor",
            "posterior_joint_draws_plus_artificial_Gaussian_correlation",
            "unregistered_double_unit_conversion",
        ],
        "completion_boundary": {
            "numerical_candidate_reactions": 3,
            "accepted_scientific_prior_reactions": 0,
            "actual_posterior_or_original_nuclear_model_available": False,
            "PRIMAT_reverse_regression_passed": True,
            "PRIMAT_cache_guard_implemented": True,
            "PRIMAT_solver_trajectory_cap_regression_passed": False,
            "PRIMAT_ETR25_curve_injection_regression_passed": False,
            "A03_nuclear_data_signoff": "pending",
            "A00_scientific_signoff": "pending",
            "A09_independent_validation": "pending",
            "task_done_allowed": False,
            "production_adapter_unlocked": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--comparators", type=Path, required=True)
    parser.add_argument("--primat-reverse-regression", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = (
        json.dumps(
            build(args.comparators, args.primat_reverse_regression),
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    if args.output is None:
        print(payload, end="")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
