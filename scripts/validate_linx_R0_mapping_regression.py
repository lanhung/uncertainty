#!/usr/bin/env python3
"""Validate the frozen LINX R0 rate-only mapping regression artifact."""

from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any


EXPECTED_REVISION = "ec2e9d2ca455e8204137e884da29f5dd13a638fa"
EXPECTED_REPOSITORY = "https://github.com/cgiovanetti/LINX"
EXPECTED_PACKAGE_SHA256 = "aacca2ad92c2132a67995801d091d9b642f3616cf7cf70b2a54a6e1d4348c745"
EXPECTED_ENVIRONMENT = {
    "equinox": "0.11.10",
    "interpax": "0.3.1",
    "jax": "0.4.28",
    "jax_backend": "cpu",
    "jax_enable_x64": True,
    "jaxlib": "0.4.28",
    "numpy": "2.4.6",
    "platform": "Linux-5.15.0-78-generic-x86_64-with-glibc2.35",
    "python": "3.11.15",
}
EXPECTED_SOURCE_HASHES = {
    "linx/reactions.py": ("5ebdb9c86978c19213d72adb3371e649ce1adffc3c8fa395dd39d0410ccbc0ee"),
    "linx/nuclear.py": ("b969043f545cfeddf41d4c3c9c376f9dfb12a52ba67cd2472f0f324f2ee126b8"),
}
EXPECTED_TABLE_HASHES = {
    "dp_gamma_he3": ("b5c410b91daaef1d4fe4b3c349f615fa9fa0a7a013a98b28b2e295574c0b4906"),
    "dd_n_he3": ("3c7aed50f298501e60279782ae638e6799c4247d265e43075a2ad2fd46225d7d"),
    "dd_p_t": ("bd9acc42dcccb9de167cc78b19e8d91c51b0f8ee5bbc2c0e155d2bd69344cc45"),
}
EXPECTED_MAPPING = {
    "dp_gamma_he3": ("dpHe3g", 1),
    "dd_n_he3": ("ddHe3n", 2),
    "dd_p_t": ("ddtp", 3),
}
EXPECTED_NETWORK_ORDER = [
    "npdg",
    "dpHe3g",
    "ddHe3n",
    "ddtp",
    "tpag",
    "tdan",
    "taLi7g",
    "He3ntp",
    "He3dap",
    "He3aBe7g",
    "Be7nLi7p",
    "Li7paa",
]
EXPECTED_Q = (-3.0, -1.0, 0.0, 1.0, 3.0)
EXPECTED_SEQUENCE = (-3.0, 3.0, -1.0, 1.0, 0.0, -3.0, 0.0, 3.0)
MIN_NORMAL = sys.float_info.min
LOG_MIN_NORMAL = math.log(MIN_NORMAL)
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def close(
    actual: float,
    expected: float,
    *,
    rel: float = 5.0e-12,
    absolute: float = 0.0,
) -> bool:
    return math.isclose(actual, expected, rel_tol=rel, abs_tol=absolute)


def expected_forward(
    temperature_t9: float,
    q: float,
    grid: list[float],
    central: list[float],
    exp_sigma: list[float],
) -> float:
    if temperature_t9 < grid[0] or temperature_t9 > grid[-1]:
        return 0.0
    perturbed = [
        center * math.exp(q * math.log(sigma)) for center, sigma in zip(central, exp_sigma)
    ]
    right = bisect.bisect_right(grid, temperature_t9)
    if right == 0:
        return perturbed[0]
    if right >= len(grid):
        return perturbed[-1]
    left = right - 1
    fraction = (temperature_t9 - grid[left]) / (grid[right] - grid[left])
    return perturbed[left] + fraction * (perturbed[right] - perturbed[left])


def load_package(_artifact_path: Path) -> dict[str, Any]:
    package_path = (
        REPOSITORY_ROOT
        / "artifacts/priors/NUCLEAR-STAGE0-R0-LINX-KEY-RECOMMENDED-v1"
        / "package.json"
    )
    if hashlib.sha256(package_path.read_bytes()).hexdigest() != EXPECTED_PACKAGE_SHA256:
        raise ValueError("frozen LINX package SHA256 drift")
    return json.loads(package_path.read_text(encoding="utf-8"))


def verify_reverse(
    row: dict[str, Any],
    detailed_balance: dict[str, Any],
    *,
    out_of_grid: bool = False,
) -> tuple[bool, float]:
    forward = float(row["forward"])
    reverse = float(row["reverse"])
    if not all(math.isfinite(value) and value >= 0.0 for value in (forward, reverse)):
        raise ValueError("rates must be finite and non-negative")
    if out_of_grid:
        if forward != 0.0 or reverse != 0.0:
            raise ValueError("upstream out-of-grid zero behavior drift")
        return False, 0.0
    if forward <= 0.0:
        if (
            row["reverse_ratio_exclusion_reason"] != "zero_forward_outside_native_grid"
            or row["reverse_over_expected_minus_one"] is not None
        ):
            raise ValueError("zero-forward reverse exclusion is not explicit")
        return False, 0.0

    temperature = float(row["T9"])
    log_expected = (
        math.log(float(detailed_balance["alpha"]))
        + float(detailed_balance["beta"]) * math.log(temperature)
        + float(detailed_balance["gamma"]) / temperature
        + math.log(forward)
    )
    stored_log = row["log_expected_reverse"]
    if stored_log is None or not close(
        float(stored_log), log_expected, rel=1.0e-13, absolute=1.0e-13
    ):
        raise ValueError("stored reverse log expectation drift")
    excluded = log_expected < LOG_MIN_NORMAL or reverse < MIN_NORMAL
    if excluded:
        if (
            row["reverse_ratio_exclusion_reason"] != "zero_or_subnormal_reverse"
            or row["reverse_over_expected_minus_one"] is not None
        ):
            raise ValueError("reverse underflow exclusion is not explicit")
        return False, 0.0

    expected = math.exp(log_expected)
    residual = reverse / expected - 1.0
    if row["reverse_ratio_exclusion_reason"] is not None or not close(
        float(row["reverse_over_expected_minus_one"]),
        residual,
        rel=1.0e-12,
        absolute=1.0e-15,
    ):
        raise ValueError("reverse same-draw residual drift")
    if not close(
        float(row["reverse_expected"]),
        expected,
        rel=1.0e-12,
        absolute=0.0,
    ):
        raise ValueError("stored reverse expectation drift")
    return True, abs(residual)


def verify_reaction(
    record: dict[str, Any],
    package_record: dict[str, Any],
    package_grid: list[float],
    forward_tolerance: float,
    reverse_tolerance: float,
    sequence_tolerance: float,
) -> dict[str, int | float]:
    canonical_id = record["canonical_id"]
    linx_id, q_index = EXPECTED_MAPPING[canonical_id]
    if (
        record["linx_id"] != linx_id
        or record["network_match_count"] != 1
        or record["nuclear_rates_q_index_zero_based"] != q_index
    ):
        raise ValueError(f"{canonical_id}: unique q-index mapping drift")

    grid = package_grid
    central = [float(value) for value in package_record["central_rate"]]
    exp_sigma = [float(value) for value in package_record["exp_sigma"]]
    if len(grid) != 150 or len(central) != len(grid) or len(exp_sigma) != len(grid):
        raise ValueError(f"{canonical_id}: package table shape drift")
    native = record["native_table"]
    if (
        native["knots"] != 150
        or not close(float(native["T9_min"]), float(grid[0]), rel=1.0e-13)
        or not close(float(native["T9_max"]), float(grid[-1]), rel=1.0e-13)
        or native["interpolation"] != "linear_in_perturbed_rate_over_T9"
    ):
        raise ValueError(f"{canonical_id}: native table contract drift")

    midpoints = [math.sqrt(left * right) for left, right in zip(grid, grid[1:])]
    probes = sorted(grid + midpoints)
    expected_pairs = {(float(temperature), q) for temperature in probes for q in EXPECTED_Q}
    rows = record["rows"]
    by_pair = {(float(row["T9"]), float(row["q"])): row for row in rows}
    if len(rows) != len(expected_pairs) or set(by_pair) != expected_pairs:
        raise ValueError(f"{canonical_id}: incomplete or duplicate probe grid")
    knot_set = {float(value) for value in grid}
    reverse_defined = 0
    reverse_excluded = 0
    max_forward = 0.0
    max_reverse = 0.0
    for (temperature, q), row in by_pair.items():
        expected_type = (
            "native_table_knot" if temperature in knot_set else "native_geometric_midpoint"
        )
        if row["probe_type"] != expected_type or not close(
            float(row["temperature_kelvin"]),
            temperature * 1.0e9,
            rel=1.0e-13,
        ):
            raise ValueError(f"{canonical_id}: temperature structure drift")
        expected = expected_forward(temperature, q, grid, central, exp_sigma)
        forward = float(row["forward"])
        residual = forward / expected - 1.0
        if not close(
            float(row["forward_expected_perturb_then_linear_interpolate"]),
            expected,
            rel=1.0e-13,
        ) or not close(
            float(row["forward_over_expected_minus_one"]),
            residual,
            rel=1.0e-12,
            absolute=1.0e-15,
        ):
            raise ValueError(f"{canonical_id}: forward transform drift")
        max_forward = max(max_forward, abs(residual))
        defined, reverse_residual = verify_reverse(row, record["detailed_balance"])
        reverse_defined += int(defined)
        reverse_excluded += int(not defined)
        max_reverse = max(max_reverse, reverse_residual)
    if max_forward > forward_tolerance or max_reverse > reverse_tolerance:
        raise ValueError(f"{canonical_id}: rate tolerance failure")

    out_rows = record["out_of_grid"]
    expected_out_pairs = {("below_native_min", q) for q in EXPECTED_Q} | {
        ("above_native_max", q) for q in EXPECTED_Q
    }
    actual_out_pairs = {(str(row["location"]), float(row["q"])) for row in out_rows}
    if len(out_rows) != 10 or actual_out_pairs != expected_out_pairs:
        raise ValueError(f"{canonical_id}: out-of-grid probe drift")
    for row in out_rows:
        if (
            row["project_policy"] != "reject_before_solver_call"
            or float(row["upstream_expected"]) != 0.0
        ):
            raise ValueError("project out-of-grid rejection policy drift")
        location = row["location"]
        expected_t = (
            float(grid[0]) * 0.5 if location == "below_native_min" else float(grid[-1]) * 1.05
        )
        if not close(float(row["T9"]), expected_t, rel=1.0e-13):
            raise ValueError("out-of-grid temperature drift")
        verify_reverse(row, record["detailed_balance"], out_of_grid=True)

    sequence = record["consecutive_draw_sequence"]
    if tuple(float(q) for q in sequence["q_sequence"]) != EXPECTED_SEQUENCE:
        raise ValueError("consecutive-draw sequence drift")
    sequence_temperatures = (
        float(grid[0]),
        0.1,
        1.0,
        float(grid[-1]),
    )
    if tuple(float(value) for value in sequence["temperatures_T9"]) != sequence_temperatures:
        raise ValueError("consecutive-draw temperatures drift")
    sequence_rows = sequence["rows"]
    expected_sequence_pairs = {
        (position, temperature)
        for position in range(len(EXPECTED_SEQUENCE))
        for temperature in sequence_temperatures
    }
    by_sequence_pair = {(int(row["position"]), float(row["T9"])): row for row in sequence_rows}
    if (
        len(sequence_rows) != len(expected_sequence_pairs)
        or set(by_sequence_pair) != expected_sequence_pairs
    ):
        raise ValueError("consecutive-draw row coverage drift")
    sequence_reverse_defined = 0
    sequence_reverse_excluded = 0
    max_sequence_forward = 0.0
    max_sequence_reverse = 0.0
    for (position, temperature), row in by_sequence_pair.items():
        q = EXPECTED_SEQUENCE[position]
        if float(row["q"]) != q:
            raise ValueError("consecutive-draw q/position drift")
        expected = expected_forward(temperature, q, grid, central, exp_sigma)
        residual = float(row["forward"]) / expected - 1.0
        if not close(float(row["forward_expected"]), expected, rel=1.0e-13) or not close(
            float(row["forward_over_expected_minus_one"]),
            residual,
            rel=1.0e-12,
            absolute=1.0e-15,
        ):
            raise ValueError("consecutive-draw forward residual drift")
        max_sequence_forward = max(max_sequence_forward, abs(residual))
        defined, reverse_residual = verify_reverse(row, record["detailed_balance"])
        sequence_reverse_defined += int(defined)
        sequence_reverse_excluded += int(not defined)
        max_sequence_reverse = max(max_sequence_reverse, reverse_residual)
    if max_sequence_forward > sequence_tolerance or max_sequence_reverse > sequence_tolerance:
        raise ValueError("consecutive-draw cache regression")

    unit = record["temperature_unit_probe"]
    if (
        float(unit["T9"]) != 1.0
        or float(unit["function_input_kelvin"]) != 1.0e9
        or unit["mistaken_1_kelvin_is_upstream_out_of_grid_zero"] is not True
        or float(unit["forward_if_mistakenly_passing_1_kelvin"]) != 0.0
    ):
        raise ValueError("temperature-unit structured probe drift")
    expected_at_one = expected_forward(1.0, 0.0, grid, central, exp_sigma)
    if not close(
        float(unit["forward_at_1e9_kelvin"]),
        expected_at_one,
        rel=forward_tolerance,
    ):
        raise ValueError("kelvin-to-T9 conversion regression")

    metrics = record["metrics"]
    expected_metrics = {
        "rows": len(rows),
        "forward_rows": len(rows),
        "reverse_ratio_defined_rows": reverse_defined,
        "reverse_ratio_excluded_rows": reverse_excluded,
        "max_abs_forward_over_expected_minus_one": max_forward,
        "max_abs_reverse_over_expected_minus_one_excluding_underflow": max_reverse,
    }
    for key, value in expected_metrics.items():
        if isinstance(value, int):
            if metrics[key] != value:
                raise ValueError(f"{canonical_id}: stored metric {key} drift")
        elif not close(float(metrics[key]), value, rel=1.0e-12, absolute=1.0e-18):
            raise ValueError(f"{canonical_id}: stored metric {key} drift")
    sequence_metrics = sequence["metrics"]
    expected_sequence_metrics = {
        "rows": len(sequence_rows),
        "reverse_ratio_defined_rows": sequence_reverse_defined,
        "reverse_ratio_excluded_rows": sequence_reverse_excluded,
        "max_abs_forward_over_expected_minus_one": max_sequence_forward,
        "max_abs_reverse_over_expected_minus_one_excluding_underflow": max_sequence_reverse,
    }
    for key, value in expected_sequence_metrics.items():
        if isinstance(value, int):
            if sequence_metrics[key] != value:
                raise ValueError(f"{canonical_id}: stored sequence metric {key} drift")
        elif not close(
            float(sequence_metrics[key]),
            value,
            rel=1.0e-12,
            absolute=1.0e-18,
        ):
            raise ValueError(f"{canonical_id}: stored sequence metric {key} drift")

    return {
        "rate_rows": len(rows),
        "reverse_defined": reverse_defined,
        "reverse_excluded": reverse_excluded,
        "out_of_grid_rows": len(out_rows),
        "sequence_rows": len(sequence_rows),
        "sequence_reverse_defined": sequence_reverse_defined,
        "sequence_reverse_excluded": sequence_reverse_excluded,
        "max_forward": max_forward,
        "max_reverse": max_reverse,
        "max_sequence_forward": max_sequence_forward,
        "max_sequence_reverse": max_sequence_reverse,
    }


def validate(path: Path) -> dict[str, int | float | bool]:
    artifact = json.loads(path.read_text(encoding="utf-8"))
    if (
        artifact["schema_version"] != 1
        or artifact["artifact_id"] != "LINX-R0-MAPPING-REGRESSION-v1"
        or artifact["status"] != "non_production_mapping_and_reverse_numerical_evidence"
    ):
        raise ValueError("artifact identity/status drift")
    scope = artifact["scope"]
    false_fields = (
        "abundance_level_UQ_run",
        "scientific_prior_selected",
        "production_adapter_unlocked",
        "signoff_provided",
    )
    if scope["task"] != "UQ0-R0-RATE-PRIOR" or any(
        scope[field] is not False for field in false_fields
    ):
        raise ValueError("artifact overstates scientific scope")

    source = artifact["source"]
    if (
        source["repository"] != EXPECTED_REPOSITORY
        or source["revision"] != EXPECTED_REVISION
        or source["network"] != "key_recommended"
        or source["tracked_worktree_matches_HEAD"] is not True
        or source["source_sha256"] != EXPECTED_SOURCE_HASHES
        or source["rate_table_sha256"] != EXPECTED_TABLE_HASHES
    ):
        raise ValueError("frozen LINX provenance drift")
    if artifact["environment"] != EXPECTED_ENVIRONMENT:
        raise ValueError("frozen W0 LINX environment drift")

    interface = artifact["interface_contract"]
    if (
        interface["network_reaction_order"] != EXPECTED_NETWORK_ORDER
        or interface["R0_canonical_order"] != list(EXPECTED_MAPPING)
        or interface["R0_linx_order"] != [value[0] for value in EXPECTED_MAPPING.values()]
        or interface["R0_q_indices_zero_based"] != [value[1] for value in EXPECTED_MAPPING.values()]
        or tuple(float(value) for value in interface["q_probes"]) != EXPECTED_Q
        or interface["all_non_R0_q_values"] != 0.0
        or interface["temperature_function_input"] != "kelvin"
        or interface["table_coordinate"] != "T9_equals_kelvin_times_1e-9"
        or interface["two_body_rate_parameter_units"] != "cm^3_s^-1_g^-1"
        or interface["upstream_out_of_grid_behavior_for_linear_tables"]
        != "zero_via_jnp_interp_left_and_right"
        or interface["project_out_of_grid_policy"] != "reject_before_solver_call"
        or interface["mutable_cache_attributes_detected"] != []
    ):
        raise ValueError("LINX R0 interface contract drift")

    underflow = artifact["underflow_policy"]
    if (
        not close(
            float(underflow["minimum_normal_float64"]),
            MIN_NORMAL,
            rel=0.0,
        )
        or underflow["excluded_rows_are_not_counted_as_reverse_identity_passes"] is not True
    ):
        raise ValueError("underflow policy drift")
    acceptance = artifact["acceptance"]
    if (
        float(acceptance["forward_relative_tolerance"]) != 5.0e-12
        or float(acceptance["reverse_relative_tolerance_excluding_underflow"]) != 5.0e-12
        or float(acceptance["consecutive_draw_relative_tolerance"]) != 5.0e-12
        or acceptance["unique_index_mapping_required"] is not True
        or acceptance["out_of_grid_zero_observation_required"] is not True
        or acceptance["project_out_of_grid_rejection_required"] is not True
        or acceptance["all_underflow_exclusions_explicit_required"] is not True
        or acceptance["passes"] is not True
    ):
        raise ValueError("acceptance contract drift")

    package = load_package(path)
    reaction_records = {record["canonical_id"]: record for record in artifact["reactions"]}
    if set(reaction_records) != set(EXPECTED_MAPPING) or len(artifact["reactions"]) != 3:
        raise ValueError("R0 reaction record coverage drift")
    results = [
        verify_reaction(
            reaction_records[canonical_id],
            package["reactions"][canonical_id],
            [float(value) for value in package["coordinate"]["grid"]],
            float(acceptance["forward_relative_tolerance"]),
            float(acceptance["reverse_relative_tolerance_excluding_underflow"]),
            float(acceptance["consecutive_draw_relative_tolerance"]),
        )
        for canonical_id in EXPECTED_MAPPING
    ]
    totals = {
        "reactions": 3,
        "unique_R0_q_indices": 3,
        "rate_rows": sum(int(result["rate_rows"]) for result in results),
        "forward_rows": sum(int(result["rate_rows"]) for result in results),
        "reverse_ratio_defined_rows": sum(int(result["reverse_defined"]) for result in results),
        "reverse_ratio_excluded_rows": sum(int(result["reverse_excluded"]) for result in results),
        "out_of_grid_rows": sum(int(result["out_of_grid_rows"]) for result in results),
        "consecutive_draw_rows": sum(int(result["sequence_rows"]) for result in results),
        "consecutive_draw_reverse_ratio_defined_rows": sum(
            int(result["sequence_reverse_defined"]) for result in results
        ),
        "consecutive_draw_reverse_ratio_excluded_rows": sum(
            int(result["sequence_reverse_excluded"]) for result in results
        ),
        "max_abs_forward_over_expected_minus_one": max(
            float(result["max_forward"]) for result in results
        ),
        "max_abs_reverse_over_expected_minus_one_excluding_underflow": max(
            float(result["max_reverse"]) for result in results
        ),
        "max_abs_consecutive_draw_forward_over_expected_minus_one": max(
            float(result["max_sequence_forward"]) for result in results
        ),
        "max_abs_consecutive_draw_reverse_over_expected_minus_one_excluding_underflow": max(
            float(result["max_sequence_reverse"]) for result in results
        ),
    }
    stored_totals = artifact["totals"]
    for key, expected in totals.items():
        actual = stored_totals[key]
        if isinstance(expected, int):
            if actual != expected:
                raise ValueError(f"stored total {key} drift")
        elif not close(float(actual), expected, rel=1.0e-12, absolute=1.0e-18):
            raise ValueError(f"stored total {key} drift")

    return {
        "reactions": 3,
        "unique_q_indices": 3,
        "rate_rows": totals["rate_rows"],
        "reverse_ratio_defined_rows": totals["reverse_ratio_defined_rows"],
        "reverse_underflow_excluded_rows": totals["reverse_ratio_excluded_rows"],
        "out_of_grid_rows": totals["out_of_grid_rows"],
        "consecutive_draw_rows": totals["consecutive_draw_rows"],
        "consecutive_draw_reverse_underflow_excluded_rows": totals[
            "consecutive_draw_reverse_ratio_excluded_rows"
        ],
        "acceptance_passes": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact", type=Path)
    args = parser.parse_args()
    print(json.dumps(validate(args.artifact), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
