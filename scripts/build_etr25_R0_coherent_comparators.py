#!/usr/bin/env python3
"""Build non-production coherent R0 comparator curves from public ETR25 tables."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from statistics import NormalDist
from typing import Any


EXPECTED_INPUT_SHA256 = "f9f7436378fe8d0985d03ca5e5b48012820948c6a391081438939b63c58df7ba"
REACTIONS = {"dp_gamma_he3", "dd_n_he3", "dd_p_t"}
Z84 = NormalDist().inv_cdf(0.84)
Q_PROBES = (-3.0, -Z84, -1.0, 0.0, Z84, 1.0, 3.0)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def quantile_matched_rate(
    median: float,
    lower_slope: float,
    upper_slope: float,
    q: float,
) -> float:
    slope = lower_slope if q < 0 else upper_slope
    return median * math.exp(slope * q)


def lognormal_proxy_rate(median: float, sigma: float, q: float) -> float:
    return median * math.exp(sigma * q)


def asymmetric_moment_ratio(
    lower_slope: float,
    upper_slope: float,
    order: int,
) -> float:
    """Return E[(R/M)^order] for the piecewise-normal quantile surrogate."""
    normal = NormalDist()
    k = float(order)
    lower = math.exp(0.5 * (k * lower_slope) ** 2) * normal.cdf(-k * lower_slope)
    upper = math.exp(0.5 * (k * upper_slope) ** 2) * normal.cdf(k * upper_slope)
    return lower + upper


def build_row(row: dict[str, Any]) -> dict[str, Any]:
    low = float(row["low_p16"])
    median = float(row["median_p50"])
    high = float(row["high_p84"])
    factor = float(row["factor_uncertainty_lognormal"])
    if not low < median < high:
        raise ValueError(f"T9={row['T9']}: quantile surrogate requires L<M<H")
    lower_width = math.log(median / low)
    upper_width = math.log(high / median)
    lower_slope = lower_width / Z84
    upper_slope = upper_width / Z84
    sigma = math.log(factor)

    reconstructed_low = quantile_matched_rate(median, lower_slope, upper_slope, -Z84)
    reconstructed_median = quantile_matched_rate(median, lower_slope, upper_slope, 0.0)
    reconstructed_high = quantile_matched_rate(median, lower_slope, upper_slope, Z84)
    relative_reconstruction_errors = {
        "p16": reconstructed_low / low - 1.0,
        "p50": reconstructed_median / median - 1.0,
        "p84": reconstructed_high / high - 1.0,
    }

    q_probe_rows = []
    for q in Q_PROBES:
        asymmetric_rate = quantile_matched_rate(median, lower_slope, upper_slope, q)
        scalar_rate = lognormal_proxy_rate(median, sigma, q)
        q_probe_rows.append(
            {
                "q": q,
                "quantile_matched_asymmetric_rate": asymmetric_rate,
                "ETR25_scalar_lognormal_rate": scalar_rate,
                "asymmetric_over_scalar": asymmetric_rate / scalar_rate,
            }
        )

    mean_ratio = asymmetric_moment_ratio(lower_slope, upper_slope, 1)
    second_moment_ratio = asymmetric_moment_ratio(lower_slope, upper_slope, 2)
    return {
        "T9": row["T9"],
        "high_temperature_matched_rate": row["high_temperature_matched_rate"],
        "source_actual_percentiles": {
            "p16": low,
            "p50": median,
            "p84": high,
        },
        "quantile_matched_asymmetric_rank1_surrogate": {
            "lower_log_slope_per_q": lower_slope,
            "upper_log_slope_per_q": upper_slope,
            "upper_over_lower_log_slope": upper_slope / lower_slope,
            "relative_quantile_reconstruction_errors": (relative_reconstruction_errors),
            "mean_over_median": mean_ratio,
            "variance_over_median_squared": (second_moment_ratio - mean_ratio * mean_ratio),
        },
        "ETR25_scalar_lognormal_proxy": {
            "sigma_log": sigma,
            "factor_uncertainty": factor,
        },
        "q_probes": q_probe_rows,
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
        rows = [build_row(row) for row in source["reactions"][reaction_id]["rows"]]
        max_reconstruction_error = max(
            abs(error)
            for row in rows
            for error in row["quantile_matched_asymmetric_rank1_surrogate"][
                "relative_quantile_reconstruction_errors"
            ].values()
        )
        slope_ratios = [
            row["quantile_matched_asymmetric_rank1_surrogate"]["upper_over_lower_log_slope"]
            for row in rows
        ]
        reactions[reaction_id] = {
            "source_table": source["reactions"][reaction_id]["table_number"],
            "source_rows_sha256": source["reactions"][reaction_id]["rows_sha256"],
            "rows": rows,
            "summary": {
                "rows": len(rows),
                "strict_L_less_M_less_H_rows": len(rows),
                "max_abs_relative_quantile_reconstruction_error": (max_reconstruction_error),
                "minimum_upper_over_lower_log_slope": min(slope_ratios),
                "maximum_upper_over_lower_log_slope": max(slope_ratios),
                "matched_high_temperature_rows": sum(
                    bool(row["high_temperature_matched_rate"]) for row in rows
                ),
            },
        }

    return {
        "schema_version": 1,
        "package_id": "ETR25-R0-COHERENT-COMPARATORS-v1",
        "task_id": "UQ0-R0-RATE-PRIOR",
        "status": (
            "candidate_comparators_complete_actual_posterior_and_scientific_signoff_pending"
        ),
        "source": {
            "path": str(input_path),
            "sha256": actual_input_sha256,
            "paper_doi": source["paper"]["doi"],
        },
        "latent_coordinate": {
            "per_reaction": "q_j~Normal(0,1)",
            "temperature_rule": "one_q_j_fixed_across_all_T_in_one_curve",
            "cross_reaction_joint_distribution": (
                "not_selected_missing_covariance_stress_contract_required"
            ),
        },
        "quantile_matched_asymmetric_rank1_surrogate": {
            "normal_quantile_Phi_inverse_0p84": Z84,
            "equation": ("ln_rate=ln_M+(ln(M/L)/z84)*q_if_q_negative_else_ln_M+(ln(H/M)/z84)*q"),
            "fixed_temperature_properties": [
                "positive",
                "continuous",
                "strictly_monotone",
                "atom_free",
                "exact_for_published_rounded_p16_p50_p84",
            ],
            "CDF_below_median": "Phi(z84*ln(rate/M)/ln(M/L))",
            "CDF_at_or_above_median": "Phi(z84*ln(rate/M)/ln(H/M))",
            "density_at_median": ("generally_discontinuous_when_lower_and_upper_slopes_differ"),
            "interpolation": {
                "coordinate": "log_T9",
                "fields": [
                    "ln_median",
                    "lower_log_slope_per_q",
                    "upper_log_slope_per_q",
                ],
                "method": "piecewise_linear",
                "out_of_grid": "reject",
                "grid_T9": [0.001, 10.0],
            },
            "temperature_copula": "imposed_comonotonic_rank_one_not_inferred",
            "curve_crossings": "prohibited_by_construction",
            "tails": "Gaussian_extrapolation_outside_p16_p84",
            "actual_posterior_reconstruction": False,
            "validated_nuclear_input_coherence": False,
            "role": "explicit_asymmetric_comparator_and_stress_model_only",
        },
        "ETR25_scalar_lognormal_proxy": {
            "equation": "rate(T,q)=median(T)*exp(q*ln(f.u.(T)))",
            "temperature_copula": "imposed_comonotonic_rank_one",
            "actual_posterior_reconstruction": False,
            "role": "ETR25_source_convention_scalar_comparator_only",
        },
        "moment_validation": {
            "formula": (
                "E[(R/M)^k]=exp((k*s_minus)^2/2)*Phi(-k*s_minus)+exp((k*s_plus)^2/2)*Phi(k*s_plus)"
            ),
            "orders_recorded": [1, 2],
        },
        "safety": {
            "claim_level": "C0_calibration",
            "scientific_prior_selected": False,
            "production_use": "prohibited",
            "actual_posterior_draws_available": False,
            "cross_reaction_covariance_known": False,
            "independence_is_default_scientific_assumption": False,
            "coherent_actual_draw_gate_closed": True,
            "required_review": [
                "A03_nuclear_data",
                "A00_scientific",
                "A09_independent_validation",
            ],
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
