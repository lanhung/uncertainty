#!/usr/bin/env python3
"""Validate the frozen PRIMAT R0 reverse-rate and cache regression artifact."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any


EXPECTED_REVISION = "21ff8f39fa18e3937e9fdf386cfa982361bfdfce"
EXPECTED_NETWORK_DATA_SHA256 = (
    "96a771b2e6c23b9d17500740f8ffc9bfecb41d89c23904de4f1a356ca677e1ec"
)
EXPECTED_CONFIG_SHA256 = (
    "ec3f905975f98d90f976456e2d2827b93e933ba92b9fef16d5f6445421fd2ce2"
)
EXPECTED_ETR25_SHA256 = (
    "f9f7436378fe8d0985d03ca5e5b48012820948c6a391081438939b63c58df7ba"
)
EXPECTED_REACTIONS = {"d_p__He3_g", "d_d__He3_n", "d_d__t_p"}
EXPECTED_Q = {-3.0, -1.0, 0.0, 1.0, 3.0}
EXPECTED_LT_MIN = 0.011604518121550084
EXPECTED_LT_MAX = 1.2764969933705093
EXPECTED_ETR25_KNOTS = [
    0.06,
    0.07,
    0.08,
    0.09,
    0.1,
    0.11,
    0.12,
    0.13,
    0.14,
    0.15,
    0.16,
    0.18,
    0.2,
    0.25,
    0.3,
    0.35,
    0.4,
    0.45,
    0.5,
    0.6,
    0.7,
    0.8,
    0.9,
    1.0,
    1.25,
    1.5,
    1.75,
    2.0,
]


def close(left: float, right: float, *, absolute: float = 1.0e-15) -> bool:
    return math.isclose(left, right, rel_tol=1.0e-13, abs_tol=absolute)


def verify_probe_grid(artifact: dict[str, Any]) -> tuple[list[float], set[float]]:
    probe = artifact["probe_grid"]
    if probe["actual_solver_temperature_trajectory_evaluated"] is not False:
        raise ValueError("artifact overstates solver-trajectory coverage")
    published = [float(value) for value in probe["registered_ETR25_primary_knots"]]
    if published != EXPECTED_ETR25_KNOTS:
        raise ValueError("registered ETR25 knot grid drift")
    expected_published_midpoints = [
        math.sqrt(left * right)
        for left, right in zip(published, published[1:])
    ]
    actual_published_midpoints = probe[
        "registered_ETR25_primary_geometric_midpoints"
    ]
    if len(actual_published_midpoints) != len(expected_published_midpoints) or any(
        not close(float(actual), expected)
        for actual, expected in zip(
            actual_published_midpoints, expected_published_midpoints
        )
    ):
        raise ValueError("ETR25 midpoint grid drift")

    config = artifact["configuration"]
    grid_min, grid_max, grid_count = config["native_rate_grid_T9"]
    native_all = [
        10.0
        ** (
            math.log10(float(grid_min))
            + index
            * (math.log10(float(grid_max)) - math.log10(float(grid_min)))
            / (int(grid_count) - 1)
        )
        for index in range(int(grid_count))
    ]
    lt_min = float(config["T9_LT_min_from_T_end"])
    lt_max = float(config["T9_LT_max_from_T_nucl"])
    expected_native = [
        value for value in native_all if lt_min <= value <= lt_max
    ]
    actual_native = [
        float(value) for value in probe["PRIMAT_native_LT_grid_knots"]
    ]
    if len(actual_native) != len(expected_native) or any(
        not close(actual, expected)
        for actual, expected in zip(actual_native, expected_native)
    ):
        raise ValueError("PRIMAT native LT knot grid drift")
    expected_native_midpoints = [
        math.sqrt(left * right)
        for left, right in zip(actual_native, actual_native[1:])
    ]
    actual_native_midpoints = [
        float(value)
        for value in probe["PRIMAT_native_LT_grid_geometric_midpoints"]
    ]
    if len(actual_native_midpoints) != len(expected_native_midpoints) or any(
        not close(actual, expected)
        for actual, expected in zip(
            actual_native_midpoints, expected_native_midpoints
        )
    ):
        raise ValueError("PRIMAT native LT midpoint grid drift")
    boundaries = [float(value) for value in probe["LT_boundary_points"]]
    if len(boundaries) != 2 or not close(boundaries[0], lt_min) or not close(
        boundaries[1], lt_max
    ):
        raise ValueError("LT boundary points drift")

    expected_full = sorted(
        set(
            published
            + expected_published_midpoints
            + actual_native
            + actual_native_midpoints
            + boundaries
        )
    )
    full = [float(value) for value in probe["full_diagnostic_grid"]]
    if len(full) != len(expected_full) or any(
        not close(actual, expected)
        for actual, expected in zip(full, expected_full)
    ):
        raise ValueError("full diagnostic grid is not the frozen union")
    expected_lt_probes = [
        temperature for temperature in full if lt_min <= temperature <= lt_max
    ]
    actual_lt_probes = [
        float(value) for value in probe["actual_LT_probe_subset"]
    ]
    if actual_lt_probes != expected_lt_probes:
        raise ValueError("actual-LT probe subset drift")
    return full, set(actual_lt_probes)


def recompute_reaction(
    record: dict[str, Any],
    temperatures: list[float],
    actual_lt_probes: set[float],
    cap_tolerance: float,
    min_normal: float,
) -> dict[str, int | float]:
    alpha = float(record["detailed_balance_coefficients"]["alpha"])
    beta = float(record["detailed_balance_coefficients"]["beta"])
    gamma = float(record["detailed_balance_coefficients"]["gamma"])
    rows = record["rows"]
    by_pair = {(float(row["T9"]), float(row["q"])): row for row in rows}
    expected_pairs = {
        (temperature, q) for temperature in temperatures for q in EXPECTED_Q
    }
    if set(by_pair) != expected_pairs or len(rows) != len(expected_pairs):
        raise ValueError(f"{record['reaction']}: incomplete or duplicate T9/q grid")
    baseline = {
        temperature: by_pair[(temperature, 0.0)] for temperature in temperatures
    }

    ratio_defined = 0
    ratio_excluded = 0
    shift_defined = 0
    shift_excluded = 0
    cap_active = 0
    cap_active_lt = 0
    max_ratio = 0.0
    max_shift = 0.0
    for (temperature, _q), row in by_pair.items():
        in_lt = temperature in actual_lt_probes
        if row["in_actual_LT_probe_subset"] is not in_lt:
            raise ValueError("row actual-LT probe flag drift")
        forward = float(row["forward"])
        reverse = float(row["reverse_unclamped"])
        reverse_clamped = float(row["reverse_clamped"])
        if not all(
            math.isfinite(value) and value >= 0.0
            for value in (forward, reverse, reverse_clamped)
        ):
            raise ValueError("rate rows must be finite and non-negative")
        factor = alpha * temperature**beta * math.exp(min(gamma / temperature, 700.0))
        if not math.isfinite(factor) or factor < 0.0:
            raise ValueError("detailed-balance factor must be finite and non-negative")
        if not close(float(row["detailed_balance_factor"]), factor):
            raise ValueError("stored detailed-balance factor drift")
        expected_reverse = factor * forward
        ratio_is_excluded = expected_reverse < min_normal or reverse < min_normal
        if ratio_is_excluded:
            ratio_excluded += 1
            if (
                row["reverse_over_expected_minus_one"] is not None
                or row["reverse_ratio_exclusion_reason"]
                != "zero_or_subnormal_reverse"
            ):
                raise ValueError("reverse exclusion is not explicit")
        else:
            ratio_defined += 1
            residual = reverse / expected_reverse - 1.0
            if row["reverse_ratio_exclusion_reason"] is not None or not close(
                float(row["reverse_over_expected_minus_one"]),
                residual,
                absolute=1.0e-18,
            ):
                raise ValueError("stored reverse residual drift")
            max_ratio = max(max_ratio, abs(residual))

        base = baseline[temperature]
        shift_is_excluded = min(
            forward,
            reverse,
            float(base["forward"]),
            float(base["reverse_unclamped"]),
        ) < min_normal
        if shift_is_excluded:
            shift_excluded += 1
            if (
                row["log_reverse_shift_minus_log_forward_shift"] is not None
                or row["log_shift_exclusion_reason"]
                != "zero_or_subnormal_forward_or_reverse"
            ):
                raise ValueError("log-shift exclusion is not explicit")
        else:
            shift_defined += 1
            residual = (
                (math.log(reverse) - math.log(forward))
                - (
                    math.log(float(base["reverse_unclamped"]))
                    - math.log(float(base["forward"]))
                )
            )
            if row["log_shift_exclusion_reason"] is not None or not close(
                float(row["log_reverse_shift_minus_log_forward_shift"]),
                residual,
                absolute=1.0e-18,
            ):
                raise ValueError("stored log-shift residual drift")
            max_shift = max(max_shift, abs(residual))

        active = reverse_clamped < reverse * (1.0 - cap_tolerance)
        if row["reverse_cap_active_within_detection_tolerance"] is not active:
            raise ValueError("stored reverse-cap decision drift")
        cap_active += int(active)
        cap_active_lt += int(active and in_lt)

    recomputed = {
        "rows": len(rows),
        "reverse_ratio_defined_rows": ratio_defined,
        "reverse_ratio_excluded_rows": ratio_excluded,
        "log_shift_defined_rows": shift_defined,
        "log_shift_excluded_rows": shift_excluded,
        "max_abs_reverse_over_expected_minus_one": max_ratio,
        "max_abs_log_reverse_shift_minus_log_forward_shift": max_shift,
        "reverse_cap_active_within_tolerance_rows": cap_active,
        "reverse_cap_active_actual_LT_probe_rows": cap_active_lt,
    }
    summary = record["summary"]
    for key, value in recomputed.items():
        if isinstance(value, float):
            if not close(float(summary[key]), value, absolute=1.0e-18):
                raise ValueError(f"{record['reaction']}: summary {key} drift")
        elif summary[key] != value:
            raise ValueError(f"{record['reaction']}: summary {key} drift")
    return recomputed


def validate(path: Path) -> dict[str, int | float | bool]:
    artifact = json.loads(path.read_text(encoding="utf-8"))
    if artifact["schema_version"] != 1:
        raise ValueError("unexpected artifact schema")
    if artifact["artifact_id"] != "PRIMAT-R0-REVERSE-REGRESSION-v1":
        raise ValueError("unexpected artifact id")
    if artifact["status"] != (
        "reverse_identity_passed_R0_cap_characterized_"
        "upstream_cache_invalidation_required"
    ):
        raise ValueError("unexpected artifact status")
    source = artifact["source"]
    if source["revision"] != EXPECTED_REVISION:
        raise ValueError("PRIMAT revision drift")
    if source["network_data_sha256"] != EXPECTED_NETWORK_DATA_SHA256:
        raise ValueError("PRIMAT network_data source drift")
    if source["imported_network_data_sha256"] != EXPECTED_NETWORK_DATA_SHA256:
        raise ValueError("installed PRIMAT differs from frozen source")
    if source["config_sha256"] != EXPECTED_CONFIG_SHA256:
        raise ValueError("PRIMAT config source drift")
    if source["ETR25_package_sha256"] != EXPECTED_ETR25_SHA256:
        raise ValueError("ETR25 temperature-source package drift")

    config = artifact["configuration"]
    if config["network"] != "small" or config["era"] != "LT":
        raise ValueError("regression did not use the registered small LT network")
    if config["native_rate_grid_T9"] != [0.001, 10.0, 1000]:
        raise ValueError("PRIMAT native rate-grid configuration drift")
    if not close(float(config["T9_LT_min_from_T_end"]), EXPECTED_LT_MIN):
        raise ValueError("PRIMAT LT minimum drift")
    if not close(float(config["T9_LT_max_from_T_nucl"]), EXPECTED_LT_MAX):
        raise ValueError("PRIMAT LT maximum drift")
    if float(config["mc_rate_rescale_cap"]) != 30.0:
        raise ValueError("PRIMAT native rate-rescale cap drift")
    if config["nuclear_qed_corrections"] is not True:
        raise ValueError("PRIMAT nuclear-QED configuration drift")
    if [float(value) for value in config["q_probes"]] != [
        -3.0,
        -1.0,
        0.0,
        1.0,
        3.0,
    ]:
        raise ValueError("q probe set drift")
    cap_tolerance = float(config["cap_relative_detection_tolerance"])
    if cap_tolerance != 1.0e-13:
        raise ValueError("cap detection tolerance drift")
    min_normal = float(config["FP64_min_normal_for_log_identity"])
    if min_normal != sys.float_info.min:
        raise ValueError("FP64 normal/subnormal boundary drift")
    acceptance = artifact["acceptance"]
    if (
        float(
            acceptance[
                "unclamped_reverse_detailed_balance_max_abs_relative_tolerance"
            ]
        )
        != 1.0e-12
        or float(acceptance["unclamped_log_shift_identity_max_abs_tolerance"])
        != 1.0e-12
    ):
        raise ValueError("reverse identity acceptance tolerance drift")

    temperatures, actual_lt_probes = verify_probe_grid(artifact)
    reactions = artifact["reactions"]
    if {record["reaction"] for record in reactions} != EXPECTED_REACTIONS:
        raise ValueError("R0 reaction coverage is incomplete")
    summaries = [
        recompute_reaction(
            record,
            temperatures,
            actual_lt_probes,
            cap_tolerance,
            min_normal,
        )
        for record in reactions
    ]
    total_ratio_exclusions = sum(
        int(summary["reverse_ratio_excluded_rows"]) for summary in summaries
    )
    total_shift_exclusions = sum(
        int(summary["log_shift_excluded_rows"]) for summary in summaries
    )
    cap_active = sum(
        int(summary["reverse_cap_active_within_tolerance_rows"])
        for summary in summaries
    )
    cap_active_lt = sum(
        int(summary["reverse_cap_active_actual_LT_probe_rows"])
        for summary in summaries
    )
    max_ratio = max(
        float(summary["max_abs_reverse_over_expected_minus_one"])
        for summary in summaries
    )
    max_shift = max(
        float(summary["max_abs_log_reverse_shift_minus_log_forward_shift"])
        for summary in summaries
    )

    if acceptance["reverse_ratio_explicit_zero_or_underflow_exclusions"] != (
        total_ratio_exclusions
    ):
        raise ValueError("aggregate reverse exclusion count drift")
    if acceptance["log_shift_explicit_zero_or_underflow_exclusions"] != (
        total_shift_exclusions
    ):
        raise ValueError("aggregate log-shift exclusion count drift")
    if acceptance["reverse_cap_active_within_tolerance_rows"] != cap_active:
        raise ValueError("aggregate cap count drift")
    if acceptance["reverse_cap_active_actual_LT_probe_rows"] != cap_active_lt:
        raise ValueError("aggregate actual-LT probe cap count drift")
    if acceptance[
        "R0_reverse_cap_not_detected_on_actual_LT_probe_points_within_tolerance"
    ] is not (cap_active_lt == 0):
        raise ValueError("actual-LT probe cap conclusion drift")
    if acceptance[
        "R0_reverse_cap_not_detected_over_full_diagnostic_grid_within_tolerance"
    ] is not (cap_active == 0):
        raise ValueError("full-grid cap conclusion drift")
    ratio_tolerance = float(
        acceptance[
            "unclamped_reverse_detailed_balance_max_abs_relative_tolerance"
        ]
    )
    shift_tolerance = float(
        acceptance["unclamped_log_shift_identity_max_abs_tolerance"]
    )
    if ratio_tolerance != 1.0e-12 or shift_tolerance != 1.0e-12:
        raise ValueError("reverse identity acceptance tolerance drift")
    if acceptance["unclamped_reverse_detailed_balance_passed"] is not (
        max_ratio <= ratio_tolerance
    ):
        raise ValueError("detailed-balance acceptance drift")
    if acceptance["unclamped_log_shift_identity_passed"] is not (
        max_shift <= shift_tolerance
    ):
        raise ValueError("log-shift acceptance drift")
    if acceptance["actual_solver_temperature_trajectory_evaluated"] is not False:
        raise ValueError("solver trajectory was not evaluated")
    if not acceptance["upstream_cache_invalidation_required"]:
        raise ValueError("upstream cache regression is hidden")
    if not acceptance["project_wrapper_guard_passed"]:
        raise ValueError("project MT/LT wrapper guard failed")
    if acceptance["production_adapter_allowed_without_cache_guard"]:
        raise ValueError("unguarded production adapter was incorrectly allowed")
    if acceptance["production_adapter_unlocked_by_this_artifact"]:
        raise ValueError("discrete native-rate regression cannot unlock production")
    if acceptance["scientific_prior_frozen_by_this_artifact"]:
        raise ValueError("numerical regression cannot freeze the scientific prior")

    cache = artifact["consecutive_draw_cache_regression"]
    if not cache["upstream_apply_variations_does_not_invalidate_fill_buffer_cache"]:
        raise ValueError("cache regression result drift")
    cases = cache["cases"]
    if len(cases) != 2 * len(EXPECTED_REACTIONS):
        raise ValueError("cache regression case coverage is incomplete")
    if not all(
        case["same_temperature_cache_hit_forward_equals_baseline"]
        and case["same_temperature_cache_hit_reverse_equals_baseline"]
        and case["after_manual_cache_clear_forward_changed"]
        for case in cases
    ):
        raise ValueError("cache regression no longer demonstrates stale/fresh split")

    guard = artifact["project_UpdateNuclearRates_wrapper_guard_regression"]
    guard_cases = guard["cases"]
    if not guard["uses_actual_UpdateNuclearRates_apply_variations_method"]:
        raise ValueError("wrapper integration did not use the pinned upstream method")
    if len(guard_cases) != 4 * len(EXPECTED_REACTIONS):
        raise ValueError("MT/LT wrapper guard case coverage is incomplete")
    if {case["era"] for case in guard_cases} != {"MT", "LT"}:
        raise ValueError("wrapper guard did not cover both eras")
    if not all(
        case["both_era_caches_invalidated_before_evaluation"]
        and case["guarded_forward_changed_from_baseline"]
        and case["guarded_reverse_changed_from_baseline"]
        for case in guard_cases
    ):
        raise ValueError("project wrapper guard integration failed")

    return {
        "reactions": len(reactions),
        "temperature_probes": len(temperatures),
        "reverse_rows": sum(int(summary["rows"]) for summary in summaries),
        "reverse_ratio_exclusions": total_ratio_exclusions,
        "log_shift_exclusions": total_shift_exclusions,
        "cache_cases": len(cases),
        "wrapper_guard_cases": len(guard_cases),
        "cap_active_within_tolerance_rows": cap_active,
        "cap_active_actual_LT_probe_rows": cap_active_lt,
        "cache_guard_required": acceptance["upstream_cache_invalidation_required"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path)
    args = parser.parse_args()
    print(json.dumps(validate(args.artifact), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
