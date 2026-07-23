#!/usr/bin/env python3
"""Quantify ETR25 R0 actual-percentile versus lognormal table differences."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Callable


EXPECTED_INPUT_SHA256 = "f9f7436378fe8d0985d03ca5e5b48012820948c6a391081438939b63c58df7ba"
REACTIONS = {"dp_gamma_he3", "dd_n_he3", "dd_p_t"}
Q_PROBES = (-3.0, -1.0, 0.0, 1.0, 3.0)
STRATA: dict[str, Callable[[dict[str, Any]], bool]] = {
    "full_table_scope": lambda row: True,
    "common_solver_evaluated_scope": lambda row: 0.06 <= row["T9"] <= 10.0,
    "primary_all_R0_unmatched_scope": lambda row: 0.06 <= row["T9"] <= 2.0,
    "shared_high_temperature_tail": lambda row: 2.5 <= row["T9"] <= 10.0,
    "reaction_specific_unmatched_scope": lambda row: not row["high_temperature_matched_rate"],
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def four_significant_digit_interval(value: float) -> tuple[float, float]:
    """Return the rounding interval implied by the four-digit source tables."""
    if not math.isfinite(value) or value <= 0:
        raise ValueError("rounding intervals require finite positive values")
    step = 10.0 ** (math.floor(math.log10(value)) - 3)
    return value - 0.5 * step, value + 0.5 * step


def contains_zero(bounds: tuple[float, float]) -> bool:
    return bounds[0] <= 0.0 <= bounds[1]


def audit_row(row: dict[str, Any]) -> dict[str, Any]:
    low = float(row["low_p16"])
    median = float(row["median_p50"])
    high = float(row["high_p84"])
    factor = float(row["factor_uncertainty_lognormal"])
    sigma = math.log(factor)
    if sigma <= 0:
        raise ValueError(f"T9={row['T9']}: expected positive lognormal sigma")

    lower_width = math.log(median / low)
    upper_width = math.log(high / median)
    predicted_low = median / factor
    predicted_high = median * factor
    low_log_residual = math.log(predicted_low / low)
    high_log_residual = math.log(predicted_high / high)

    low_min, low_max = four_significant_digit_interval(low)
    median_min, median_max = four_significant_digit_interval(median)
    high_min, high_max = four_significant_digit_interval(high)
    factor_min, factor_max = four_significant_digit_interval(factor)
    low_residual_bounds = (
        math.log((median_min / factor_max) / low_max),
        math.log((median_max / factor_min) / low_min),
    )
    high_residual_bounds = (
        math.log((median_min * factor_min) / high_max),
        math.log((median_max * factor_max) / high_min),
    )
    scale_mismatch_bounds = (
        0.5 * math.log(high_min / low_max) - math.log(factor_max),
        0.5 * math.log(high_max / low_min) - math.log(factor_min),
    )
    asymmetry_bounds = (
        math.log((high_min * low_min) / (median_max * median_max)),
        math.log((high_max * low_max) / (median_min * median_min)),
    )

    max_coherent_reconstruction_error = 0.0
    for q in Q_PROBES:
        rate = median * math.exp(q * sigma)
        reconstructed_q = math.log(rate / median) / sigma
        max_coherent_reconstruction_error = max(
            max_coherent_reconstruction_error,
            abs(reconstructed_q - q),
        )

    return {
        **row,
        "actual_lower_log_width": lower_width,
        "actual_upper_log_width": upper_width,
        "actual_log_width_asymmetry_upper_minus_lower": upper_width - lower_width,
        "actual_log_geometric_center_shift": 0.5 * (upper_width - lower_width),
        "lognormal_scale_mismatch_actual_average_width_minus_sigma": (
            0.5 * (upper_width + lower_width) - sigma
        ),
        "relative_log_width_asymmetry": (
            abs(upper_width - lower_width) / (0.5 * (upper_width + lower_width))
        ),
        "lognormal_sigma_ln_factor_uncertainty": sigma,
        "lognormal_predicted_lower_68_endpoint": predicted_low,
        "lognormal_predicted_upper_68_endpoint": predicted_high,
        "lower_endpoint_log_residual_predicted_over_actual_p16": low_log_residual,
        "upper_endpoint_log_residual_predicted_over_actual_p84": high_log_residual,
        "lower_endpoint_relative_error_predicted_over_actual_p16": (predicted_low / low - 1.0),
        "upper_endpoint_relative_error_predicted_over_actual_p84": (predicted_high / high - 1.0),
        "four_significant_digit_rounding": {
            "lower_endpoint_log_residual_bounds": list(low_residual_bounds),
            "upper_endpoint_log_residual_bounds": list(high_residual_bounds),
            "scale_mismatch_log_bounds": list(scale_mismatch_bounds),
            "actual_log_asymmetry_bounds": list(asymmetry_bounds),
            "lower_endpoint_difference_resolved": not contains_zero(low_residual_bounds),
            "upper_endpoint_difference_resolved": not contains_zero(high_residual_bounds),
            "scale_mismatch_resolved": not contains_zero(scale_mismatch_bounds),
            "actual_log_asymmetry_resolved": not contains_zero(asymmetry_bounds),
        },
        "scalar_coherent_probe": {
            "q_values": list(Q_PROBES),
            "one_q_held_across_temperature": True,
            "max_abs_reconstructed_q_error_at_this_temperature": (
                max_coherent_reconstruction_error
            ),
        },
    }


def location_record(rows: list[dict[str, Any]], field: str) -> dict[str, float | str | bool]:
    candidates: list[tuple[float, dict[str, Any], str]] = []
    if field == "quantile_log_residual":
        for row in rows:
            candidates.extend(
                [
                    (
                        abs(row["lower_endpoint_log_residual_predicted_over_actual_p16"]),
                        row,
                        "p16",
                    ),
                    (
                        abs(row["upper_endpoint_log_residual_predicted_over_actual_p84"]),
                        row,
                        "p84",
                    ),
                ]
            )
    else:
        for row in rows:
            candidates.append((abs(float(row[field])), row, field))
    value, row, side = max(candidates, key=lambda item: item[0])
    return {
        "absolute_value": value,
        "T9": row["T9"],
        "side_or_field": side,
        "high_temperature_matched_rate": row["high_temperature_matched_rate"],
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        raise ValueError("cannot summarize an empty audit stratum")
    residuals = [
        row[field]
        for row in rows
        for field in (
            "lower_endpoint_log_residual_predicted_over_actual_p16",
            "upper_endpoint_log_residual_predicted_over_actual_p84",
        )
    ]
    relative_errors = [
        row[field]
        for row in rows
        for field in (
            "lower_endpoint_relative_error_predicted_over_actual_p16",
            "upper_endpoint_relative_error_predicted_over_actual_p84",
        )
    ]
    rounding = [row["four_significant_digit_rounding"] for row in rows]
    return {
        "rows": len(rows),
        "T9_min": min(row["T9"] for row in rows),
        "T9_max": max(row["T9"] for row in rows),
        "matched_high_temperature_rows": sum(
            bool(row["high_temperature_matched_rate"]) for row in rows
        ),
        "max_abs_log_quantile_residual": location_record(rows, "quantile_log_residual"),
        "rms_log_quantile_residual": math.sqrt(
            sum(value * value for value in residuals) / len(residuals)
        ),
        "max_abs_relative_quantile_error": max(map(abs, relative_errors)),
        "max_abs_actual_log_width_asymmetry": location_record(
            rows, "actual_log_width_asymmetry_upper_minus_lower"
        ),
        "max_abs_lognormal_scale_mismatch": location_record(
            rows, "lognormal_scale_mismatch_actual_average_width_minus_sigma"
        ),
        "max_relative_log_width_asymmetry": max(
            row["relative_log_width_asymmetry"] for row in rows
        ),
        "rounding_resolved_lower_endpoint_rows": sum(
            bool(item["lower_endpoint_difference_resolved"]) for item in rounding
        ),
        "rounding_resolved_upper_endpoint_rows": sum(
            bool(item["upper_endpoint_difference_resolved"]) for item in rounding
        ),
        "rounding_resolved_any_endpoint_rows": sum(
            bool(
                item["lower_endpoint_difference_resolved"]
                or item["upper_endpoint_difference_resolved"]
            )
            for item in rounding
        ),
        "rounding_resolved_scale_mismatch_rows": sum(
            bool(item["scale_mismatch_resolved"]) for item in rounding
        ),
        "rounding_resolved_actual_log_asymmetry_rows": sum(
            bool(item["actual_log_asymmetry_resolved"]) for item in rounding
        ),
        "max_scalar_coherent_q_reconstruction_error": max(
            row["scalar_coherent_probe"]["max_abs_reconstructed_q_error_at_this_temperature"]
            for row in rows
        ),
    }


def build(input_path: Path) -> dict[str, Any]:
    actual_input_sha256 = sha256(input_path)
    if actual_input_sha256 != EXPECTED_INPUT_SHA256:
        raise ValueError(
            f"input package SHA256 mismatch: {actual_input_sha256} != {EXPECTED_INPUT_SHA256}"
        )
    source = json.loads(input_path.read_text(encoding="utf-8"))
    if set(source["reactions"]) != REACTIONS:
        raise ValueError("ETR25 package must contain exactly the three R0 reactions")

    reactions: dict[str, Any] = {}
    for reaction_id in sorted(REACTIONS):
        audited_rows = [audit_row(row) for row in source["reactions"][reaction_id]["rows"]]
        reactions[reaction_id] = {
            "source_table": source["reactions"][reaction_id]["table_number"],
            "source_rows_sha256": source["reactions"][reaction_id]["rows_sha256"],
            "summaries": {
                name: summarize([row for row in audited_rows if predicate(row)])
                for name, predicate in STRATA.items()
            },
            "rows": audited_rows,
        }

    primary_grids = [
        [row["T9"] for row in reaction["rows"] if STRATA["primary_all_R0_unmatched_scope"](row)]
        for reaction in reactions.values()
    ]
    if not all(grid == primary_grids[0] for grid in primary_grids[1:]):
        raise ValueError("primary audit stratum must use one shared grid")
    if len(primary_grids[0]) != 28 or min(primary_grids[0]) != 0.06 or max(primary_grids[0]) != 2.0:
        raise ValueError("unexpected primary all-R0 audit stratum")

    return {
        "schema_version": 1,
        "audit_id": "ETR25-R0-RATE-PDF-AUDIT-v1",
        "task_id": "UQ0-RATE-PDF-AUDIT",
        "status": "descriptive_rate_pdf_audit_complete_production_prohibited",
        "source": {
            "package": str(input_path),
            "package_sha256": actual_input_sha256,
            "paper_doi": source["paper"]["doi"],
            "table_semantics": (
                "p16_p50_p84_are_actual_pointwise_percentiles_"
                "factor_uncertainty_is_separate_lognormal_approximation"
            ),
        },
        "temperature_scopes": {
            "full_table_scope": {
                "T9": [0.001, 10.0],
                "knots": 60,
                "role": "publisher_product_integrity_and_descriptive_audit",
            },
            "common_solver_evaluated_scope": {
                "T9": [0.06, 10.0],
                "knots": 38,
                "role": "intersection_of_three_accepted_solver_network_domains",
            },
            "primary_all_R0_unmatched_scope": {
                "T9": [0.06, 2.0],
                "knots": 28,
                "role": (
                    "primary_descriptive_audit_intersection_of_solver_domains_"
                    "and_all_three_unmatched_ETR25_table_segments"
                ),
                "not_a_physical_sensitivity_window": True,
            },
            "shared_high_temperature_tail": {
                "T9": [2.5, 10.0],
                "knots": 10,
                "role": (
                    "separate_lineage_stratum_both_dd_rates_matched_from_2p5_"
                    "and_dp_gamma_matched_from_5"
                ),
            },
            "impact_sensitivity_window": {
                "status": "not_yet_measured",
                "required_experiment": (
                    "preregistered_localized_coherent_rate_response_with_"
                    "detailed_balance_and_second_solver_boundary_replication"
                ),
            },
        },
        "solver_domain_evidence": {
            "LINX": {
                "revision": "ec2e9d2ca455e8204137e884da29f5dd13a638fa",
                "network_domain_T9": [0.06, 100.0],
                "source_anchors": [
                    "linx/const.py:T_start,T_end",
                    "linx/abundances.py:AbundanceModel.__call__,diffeqsolve",
                ],
            },
            "PRyMordial": {
                "revision": "725d8a8db3ad5ea2630580d825c9d0d69ed76533",
                "network_domain_T9": [0.0116045, 11.6045],
                "source_anchors": [
                    "PRyM/PRyM_init.py:T_weak,T_nucl,T_end",
                    "PRyM/PRyM_main.py:mid_and_low_temperature_networks",
                ],
            },
            "PRIMAT": {
                "revision": "21ff8f39fa18e3937e9fdf386cfa982361bfdfce",
                "network_domain_T9": [0.0116045, 11.6045],
                "source_anchors": [
                    "primat/constants.py:MT9i,MT9f,LT9f",
                    "primat/network_data.py:small_network_R0_membership",
                    "primat/nuclear_network.py:MT_and_LT_network_integration",
                ],
            },
        },
        "rounding_model": {
            "source_significant_digits": 4,
            "assumption": "round_to_nearest_at_four_significant_digits",
            "interval": "displayed_value_plus_or_minus_half_last_decimal_unit",
            "purpose": (
                "distinguish_descriptive_residuals_resolved_by_published_"
                "precision_from_values_compatible_with_table_rounding"
            ),
        },
        "scalar_coherent_validation": {
            "equation": "rate(T,q)=median(T)*exp(q*ln(f.u.(T)))",
            "endpoint_convention": (
                "ETR25_68_percent_factor_uncertainty_q_plus_or_minus_one_"
                "not_exact_Normal_p16_p84_z_score"
            ),
            "q_probe_values": list(Q_PROBES),
            "same_q_at_every_temperature_in_one_reaction_realization": True,
            "independent_temperature_noise_prohibited": True,
            "actual_posterior_curve_claim": False,
            "actual_posterior_coherence": ("not_evaluable_from_public_pointwise_quantiles"),
        },
        "decision": {
            "scalar_lognormal_status": ("accepted_as_explicit_coherent_comparator_only"),
            "actual_pointwise_percentile_status": ("captured_and_quantitatively_compared"),
            "actual_functional_posterior_status": ("unavailable_in_identified_public_release"),
            "equivalence_claim_allowed": False,
            "cross_reaction_independence_claim_allowed": False,
            "scientific_label_generation_allowed": False,
            "production_use": "prohibited_pending_coherent_prior_and_downstream_gates",
        },
        "reactions": reactions,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = json.dumps(build(args.input), indent=2, sort_keys=True) + "\n"
    if args.output is None:
        print(payload, end="")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
