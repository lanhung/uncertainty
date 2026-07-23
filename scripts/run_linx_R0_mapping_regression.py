#!/usr/bin/env python3
"""Generate the frozen LINX R0 scalar-rate mapping regression artifact.

This diagnostic evaluates rate functions only.  It does not run a BBN
abundance solve and it does not select or approve a production nuclear prior.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np


EXPECTED_REVISION = "ec2e9d2ca455e8204137e884da29f5dd13a638fa"
NETWORK = "key_recommended"
Q_PROBES = (-3.0, -1.0, 0.0, 1.0, 3.0)
REACTIONS = (
    {
        "canonical_id": "dp_gamma_he3",
        "linx_id": "dpHe3g",
        "q_index": 1,
        "table": "linx/data/nuclear_rates/key_recommended/dpHe3g.txt",
        "table_sha256": ("b5c410b91daaef1d4fe4b3c349f615fa9fa0a7a013a98b28b2e295574c0b4906"),
    },
    {
        "canonical_id": "dd_n_he3",
        "linx_id": "ddHe3n",
        "q_index": 2,
        "table": "linx/data/nuclear_rates/key_recommended/ddHe3n.txt",
        "table_sha256": ("3c7aed50f298501e60279782ae638e6799c4247d265e43075a2ad2fd46225d7d"),
    },
    {
        "canonical_id": "dd_p_t",
        "linx_id": "ddtp",
        "q_index": 3,
        "table": "linx/data/nuclear_rates/key_recommended/ddtp.txt",
        "table_sha256": ("bd9acc42dcccb9de167cc78b19e8d91c51b0f8ee5bbc2c0e155d2bd69344cc45"),
    },
)
EXPECTED_SOURCE_HASHES = {
    "linx/reactions.py": ("5ebdb9c86978c19213d72adb3371e649ce1adffc3c8fa395dd39d0410ccbc0ee"),
    "linx/nuclear.py": ("b969043f545cfeddf41d4c3c9c376f9dfb12a52ba67cd2472f0f324f2ee126b8"),
}
MIN_NORMAL = sys.float_info.min
LOG_MIN_NORMAL = math.log(MIN_NORMAL)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def relative_residual(actual: float, expected: float) -> float:
    if expected == 0.0:
        return 0.0 if actual == 0.0 else math.inf
    return actual / expected - 1.0


def evaluate(reaction: Any, temperature_t9: float, q: float) -> tuple[float, float]:
    forward, reverse = evaluate_many(reaction, np.asarray([temperature_t9], dtype=np.float64), q)
    return float(forward[0]), float(reverse[0])


def evaluate_many(
    reaction: Any, temperatures_t9: np.ndarray, q: float
) -> tuple[np.ndarray, np.ndarray]:
    temperature_kelvin = temperatures_t9 * 1.0e9
    return (
        np.asarray(reaction.frwrd_rate_param(temperature_kelvin, q), dtype=np.float64),
        np.asarray(reaction.bkwrd_rate_param(temperature_kelvin, q), dtype=np.float64),
    )


def expected_forward(
    temperature_t9: float,
    q: float,
    grid: np.ndarray,
    central: np.ndarray,
    exp_sigma: np.ndarray,
) -> float:
    perturbed = central * np.exp(q * np.log(exp_sigma))
    return float(np.interp(temperature_t9, grid, perturbed, left=0.0, right=0.0))


def reverse_check(
    reaction: Any,
    temperature_t9: float,
    forward: float,
    reverse: float,
) -> dict[str, Any]:
    if forward <= 0.0:
        return {
            "reverse_expected": 0.0,
            "reverse_over_expected_minus_one": None,
            "reverse_ratio_exclusion_reason": "zero_forward_outside_native_grid",
            "log_expected_reverse": None,
        }
    log_expected = (
        math.log(float(reaction.alpha))
        + float(reaction.beta) * math.log(temperature_t9)
        + float(reaction.gamma) / temperature_t9
        + math.log(forward)
    )
    if log_expected < LOG_MIN_NORMAL or reverse < MIN_NORMAL:
        return {
            "reverse_expected": (
                0.0
                if log_expected < math.log(sys.float_info.min * sys.float_info.epsilon)
                else math.exp(log_expected)
            ),
            "reverse_over_expected_minus_one": None,
            "reverse_ratio_exclusion_reason": "zero_or_subnormal_reverse",
            "log_expected_reverse": log_expected,
        }
    expected = math.exp(log_expected)
    return {
        "reverse_expected": expected,
        "reverse_over_expected_minus_one": relative_residual(reverse, expected),
        "reverse_ratio_exclusion_reason": None,
        "log_expected_reverse": log_expected,
    }


def audit_reaction(network: Any, spec: dict[str, Any]) -> dict[str, Any]:
    matches = [
        (index, reaction)
        for index, reaction in enumerate(network.reactions)
        if reaction.name == spec["linx_id"]
    ]
    if len(matches) != 1:
        raise RuntimeError(f"{spec['linx_id']}: expected one network match, found {len(matches)}")
    index, reaction = matches[0]
    if index != spec["q_index"]:
        raise RuntimeError(f"{spec['linx_id']}: q-index drift {index} != {spec['q_index']}")
    if reaction.interp_type != "linear":
        raise RuntimeError(f"{spec['linx_id']}: interpolation is not linear")

    grid = np.asarray(reaction.T9_vec, dtype=np.float64)
    central = np.asarray(reaction.mu_median_vec, dtype=np.float64)
    exp_sigma = np.asarray(reaction.expsigma_vec, dtype=np.float64)
    if (
        grid.ndim != 1
        or len(grid) != 150
        or central.shape != grid.shape
        or exp_sigma.shape != grid.shape
        or not np.all(np.diff(grid) > 0.0)
    ):
        raise RuntimeError(f"{spec['linx_id']}: malformed native rate table")

    midpoints = np.sqrt(grid[:-1] * grid[1:])
    probes = np.sort(np.concatenate((grid, midpoints)))
    knot_values = {float(value) for value in grid}
    rows: list[dict[str, Any]] = []
    max_forward_residual = 0.0
    max_reverse_residual = 0.0
    reverse_defined = 0
    reverse_excluded = 0
    for q in Q_PROBES:
        forward_values, reverse_values = evaluate_many(reaction, probes, q)
        for temperature_t9, forward_value, reverse_value in zip(
            probes, forward_values, reverse_values
        ):
            temperature = float(temperature_t9)
            forward = float(forward_value)
            reverse = float(reverse_value)
            expected = expected_forward(temperature, q, grid, central, exp_sigma)
            forward_residual = relative_residual(forward, expected)
            max_forward_residual = max(max_forward_residual, abs(forward_residual))
            reverse_result = reverse_check(reaction, temperature, forward, reverse)
            reverse_residual = reverse_result["reverse_over_expected_minus_one"]
            if reverse_residual is None:
                reverse_excluded += 1
            else:
                reverse_defined += 1
                max_reverse_residual = max(max_reverse_residual, abs(reverse_residual))
            rows.append(
                {
                    "T9": temperature,
                    "temperature_kelvin": temperature * 1.0e9,
                    "probe_type": (
                        "native_table_knot"
                        if temperature in knot_values
                        else "native_geometric_midpoint"
                    ),
                    "q": q,
                    "forward": forward,
                    "forward_expected_perturb_then_linear_interpolate": expected,
                    "forward_over_expected_minus_one": forward_residual,
                    "reverse": reverse,
                    **reverse_result,
                }
            )

    out_of_grid: list[dict[str, Any]] = []
    out_of_grid_locations = (
        ("below_native_min", float(grid[0]) * 0.5),
        ("above_native_max", float(grid[-1]) * 1.05),
    )
    out_of_grid_temperatures = np.asarray(
        [temperature for _label, temperature in out_of_grid_locations],
        dtype=np.float64,
    )
    for q in Q_PROBES:
        forward_values, reverse_values = evaluate_many(reaction, out_of_grid_temperatures, q)
        for (label, temperature), forward_value, reverse_value in zip(
            out_of_grid_locations, forward_values, reverse_values
        ):
            out_of_grid.append(
                {
                    "location": label,
                    "T9": temperature,
                    "temperature_kelvin": temperature * 1.0e9,
                    "q": q,
                    "forward": float(forward_value),
                    "reverse": float(reverse_value),
                    "upstream_expected": 0.0,
                    "project_policy": "reject_before_solver_call",
                }
            )

    sequence = (-3.0, 3.0, -1.0, 1.0, 0.0, -3.0, 0.0, 3.0)
    sequence_temperatures = (
        float(grid[0]),
        0.1,
        1.0,
        float(grid[-1]),
    )
    sequence_rows: list[dict[str, Any]] = []
    max_sequence_forward_residual = 0.0
    max_sequence_reverse_residual = 0.0
    sequence_reverse_defined = 0
    sequence_reverse_excluded = 0
    sequence_temperature_array = np.asarray(sequence_temperatures, dtype=np.float64)
    for position, q in enumerate(sequence):
        forward_values, reverse_values = evaluate_many(reaction, sequence_temperature_array, q)
        for temperature, forward_value, reverse_value in zip(
            sequence_temperatures, forward_values, reverse_values
        ):
            forward = float(forward_value)
            reverse = float(reverse_value)
            expected = expected_forward(temperature, q, grid, central, exp_sigma)
            forward_residual = relative_residual(forward, expected)
            max_sequence_forward_residual = max(
                max_sequence_forward_residual, abs(forward_residual)
            )
            reverse_result = reverse_check(reaction, temperature, forward, reverse)
            reverse_residual = reverse_result["reverse_over_expected_minus_one"]
            if reverse_residual is None:
                sequence_reverse_excluded += 1
            else:
                sequence_reverse_defined += 1
                max_sequence_reverse_residual = max(
                    max_sequence_reverse_residual, abs(reverse_residual)
                )
            sequence_rows.append(
                {
                    "position": position,
                    "T9": temperature,
                    "q": q,
                    "forward": forward,
                    "forward_expected": expected,
                    "forward_over_expected_minus_one": forward_residual,
                    "reverse": reverse,
                    **reverse_result,
                }
            )

    unit_temperature_t9 = 1.0
    unit_forward, unit_reverse = evaluate(reaction, unit_temperature_t9, 0.0)
    raw_kelvin_forward = float(reaction.frwrd_rate_param(1.0, 0.0))
    return {
        "canonical_id": spec["canonical_id"],
        "linx_id": spec["linx_id"],
        "network_match_count": len(matches),
        "nuclear_rates_q_index_zero_based": index,
        "native_table": {
            "T9_min": float(grid[0]),
            "T9_max": float(grid[-1]),
            "knots": len(grid),
            "interpolation": "linear_in_perturbed_rate_over_T9",
            "perturbation": "mu_median*exp(q*log(exp_sigma))",
        },
        "states": {
            "in": list(reaction.in_states),
            "out": list(reaction.out_states),
        },
        "symmetry_factors": {
            "forward": float(reaction.frwrd_symmetry_fac),
            "reverse": float(reaction.bkwrd_symmetry_fac),
        },
        "detailed_balance": {
            "formula": "reverse=alpha*T9**beta*exp(gamma/T9)*forward_same_q",
            "alpha": float(reaction.alpha),
            "beta": float(reaction.beta),
            "gamma": float(reaction.gamma),
        },
        "rows": rows,
        "metrics": {
            "rows": len(rows),
            "forward_rows": len(rows),
            "reverse_ratio_defined_rows": reverse_defined,
            "reverse_ratio_excluded_rows": reverse_excluded,
            "max_abs_forward_over_expected_minus_one": max_forward_residual,
            "max_abs_reverse_over_expected_minus_one_excluding_underflow": (max_reverse_residual),
        },
        "out_of_grid": out_of_grid,
        "consecutive_draw_sequence": {
            "q_sequence": list(sequence),
            "temperatures_T9": list(sequence_temperatures),
            "rows": sequence_rows,
            "metrics": {
                "rows": len(sequence_rows),
                "reverse_ratio_defined_rows": sequence_reverse_defined,
                "reverse_ratio_excluded_rows": sequence_reverse_excluded,
                "max_abs_forward_over_expected_minus_one": (max_sequence_forward_residual),
                "max_abs_reverse_over_expected_minus_one_excluding_underflow": (
                    max_sequence_reverse_residual
                ),
            },
        },
        "temperature_unit_probe": {
            "T9": unit_temperature_t9,
            "function_input_kelvin": 1.0e9,
            "forward_at_1e9_kelvin": unit_forward,
            "reverse_at_1e9_kelvin": unit_reverse,
            "forward_if_mistakenly_passing_1_kelvin": raw_kelvin_forward,
            "mistaken_1_kelvin_is_upstream_out_of_grid_zero": (raw_kelvin_forward == 0.0),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--linx-source-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    source_root = args.linx_source_root.resolve()
    revision = git(source_root, "rev-parse", "HEAD")
    if revision != EXPECTED_REVISION:
        raise RuntimeError(f"LINX revision drift: {revision}")
    tracked_diff = subprocess.run(
        ["git", "diff", "--quiet", "HEAD", "--"],
        cwd=source_root,
        check=False,
    ).returncode
    if tracked_diff != 0:
        raise RuntimeError("LINX source checkout has tracked modifications")

    source_hashes = {path: sha256(source_root / path) for path in EXPECTED_SOURCE_HASHES}
    if source_hashes != EXPECTED_SOURCE_HASHES:
        raise RuntimeError(f"LINX source hash drift: {source_hashes}")
    table_hashes = {spec["canonical_id"]: sha256(source_root / spec["table"]) for spec in REACTIONS}
    expected_table_hashes = {spec["canonical_id"]: spec["table_sha256"] for spec in REACTIONS}
    if table_hashes != expected_table_hashes:
        raise RuntimeError(f"LINX table hash drift: {table_hashes}")

    os.environ.setdefault("JAX_ENABLE_X64", "True")
    sys.path.insert(0, str(source_root))
    import jax  # pylint: disable=import-outside-toplevel
    from linx.nuclear import NuclearRates  # pylint: disable=import-outside-toplevel

    if not jax.config.x64_enabled:
        raise RuntimeError("JAX x64 must be enabled for the frozen regression")
    network = NuclearRates(nuclear_net=NETWORK)
    records = [audit_reaction(network, spec) for spec in REACTIONS]
    indices = [record["nuclear_rates_q_index_zero_based"] for record in records]
    if len(set(indices)) != len(indices):
        raise RuntimeError(f"R0 q indices are not unique: {indices}")

    all_objects = [network, *network.reactions]
    cache_attributes = sorted(
        {name for obj in all_objects for name in dir(obj) if "cache" in name.lower()}
    )
    totals = {
        "reactions": len(records),
        "unique_R0_q_indices": len(set(indices)),
        "rate_rows": sum(record["metrics"]["rows"] for record in records),
        "forward_rows": sum(record["metrics"]["forward_rows"] for record in records),
        "reverse_ratio_defined_rows": sum(
            record["metrics"]["reverse_ratio_defined_rows"] for record in records
        ),
        "reverse_ratio_excluded_rows": sum(
            record["metrics"]["reverse_ratio_excluded_rows"] for record in records
        ),
        "out_of_grid_rows": sum(len(record["out_of_grid"]) for record in records),
        "consecutive_draw_rows": sum(
            record["consecutive_draw_sequence"]["metrics"]["rows"] for record in records
        ),
        "consecutive_draw_reverse_ratio_defined_rows": sum(
            record["consecutive_draw_sequence"]["metrics"]["reverse_ratio_defined_rows"]
            for record in records
        ),
        "consecutive_draw_reverse_ratio_excluded_rows": sum(
            record["consecutive_draw_sequence"]["metrics"]["reverse_ratio_excluded_rows"]
            for record in records
        ),
        "max_abs_forward_over_expected_minus_one": max(
            record["metrics"]["max_abs_forward_over_expected_minus_one"] for record in records
        ),
        "max_abs_reverse_over_expected_minus_one_excluding_underflow": max(
            record["metrics"]["max_abs_reverse_over_expected_minus_one_excluding_underflow"]
            for record in records
        ),
        "max_abs_consecutive_draw_forward_over_expected_minus_one": max(
            record["consecutive_draw_sequence"]["metrics"][
                "max_abs_forward_over_expected_minus_one"
            ]
            for record in records
        ),
        "max_abs_consecutive_draw_reverse_over_expected_minus_one_excluding_underflow": max(
            record["consecutive_draw_sequence"]["metrics"][
                "max_abs_reverse_over_expected_minus_one_excluding_underflow"
            ]
            for record in records
        ),
    }
    artifact = {
        "schema_version": 1,
        "artifact_id": "LINX-R0-MAPPING-REGRESSION-v1",
        "generated_at_utc": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "status": "non_production_mapping_and_reverse_numerical_evidence",
        "scope": {
            "task": "UQ0-R0-RATE-PRIOR",
            "abundance_level_UQ_run": False,
            "scientific_prior_selected": False,
            "production_adapter_unlocked": False,
            "signoff_provided": False,
            "allowed_use": (
                "LINX native scalar-envelope mapping, reverse-rate, "
                "temperature-boundary, and stateless consecutive-draw evidence"
            ),
        },
        "source": {
            "repository": "https://github.com/cgiovanetti/LINX",
            "revision": revision,
            "network": NETWORK,
            "tracked_worktree_matches_HEAD": True,
            "source_sha256": source_hashes,
            "rate_table_sha256": table_hashes,
        },
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "jax": importlib.metadata.version("jax"),
            "jaxlib": importlib.metadata.version("jaxlib"),
            "equinox": importlib.metadata.version("equinox"),
            "interpax": importlib.metadata.version("interpax"),
            "numpy": np.__version__,
            "jax_enable_x64": bool(jax.config.x64_enabled),
            "jax_backend": jax.default_backend(),
        },
        "interface_contract": {
            "network_reaction_order": list(network.reactions_names),
            "R0_canonical_order": [spec["canonical_id"] for spec in REACTIONS],
            "R0_linx_order": [spec["linx_id"] for spec in REACTIONS],
            "R0_q_indices_zero_based": indices,
            "q_probes": list(Q_PROBES),
            "all_non_R0_q_values": 0.0,
            "temperature_function_input": "kelvin",
            "table_coordinate": "T9_equals_kelvin_times_1e-9",
            "two_body_rate_parameter_units": "cm^3_s^-1_g^-1",
            "unit_evidence": ("frozen linx/reactions.py Reaction docstring and implementation"),
            "upstream_out_of_grid_behavior_for_linear_tables": (
                "zero_via_jnp_interp_left_and_right"
            ),
            "project_out_of_grid_policy": "reject_before_solver_call",
            "mutable_cache_attributes_detected": cache_attributes,
            "consecutive_draw_execution": (
                "same frozen Reaction objects repeatedly evaluated without "
                "reinstantiation in a non-monotone repeated q sequence"
            ),
        },
        "underflow_policy": {
            "minimum_normal_float64": MIN_NORMAL,
            "comparison_rule": (
                "exclude reverse ratio if expected or observed reverse is zero "
                "or subnormal; store an explicit exclusion reason per row"
            ),
            "excluded_rows_are_not_counted_as_reverse_identity_passes": True,
        },
        "reactions": records,
        "totals": totals,
        "acceptance": {
            "forward_relative_tolerance": 5.0e-12,
            "reverse_relative_tolerance_excluding_underflow": 5.0e-12,
            "consecutive_draw_relative_tolerance": 5.0e-12,
            "unique_index_mapping_required": True,
            "out_of_grid_zero_observation_required": True,
            "project_out_of_grid_rejection_required": True,
            "all_underflow_exclusions_explicit_required": True,
            "passes": (
                totals["unique_R0_q_indices"] == 3
                and totals["max_abs_forward_over_expected_minus_one"] <= 5.0e-12
                and totals["max_abs_reverse_over_expected_minus_one_excluding_underflow"] <= 5.0e-12
                and totals["max_abs_consecutive_draw_forward_over_expected_minus_one"] <= 5.0e-12
                and totals[
                    "max_abs_consecutive_draw_reverse_over_expected_minus_one_excluding_underflow"
                ]
                <= 5.0e-12
                and all(
                    row["forward"] == 0.0 and row["reverse"] == 0.0
                    for record in records
                    for row in record["out_of_grid"]
                )
            ),
        },
        "interpretation": {
            "supported": (
                "At the frozen LINX revision and key_recommended network, the "
                "three R0 scalar coordinates map uniquely to q indices 1,2,3; "
                "the native forward transform and same-q reverse formula pass "
                "the stored FP64 rate-only probes, excluding explicitly marked "
                "reverse underflow rows; repeated draws show no mutable-rate "
                "cache contamination."
            ),
            "not_supported": [
                "selection of a scientific or production nuclear prior",
                "actual ETR25 posterior reconstruction",
                "abundance-level uncertainty propagation",
                "cross-solver engine-discrepancy claims",
                "temperature-continuum proof between stored probes",
                "scientific or independent-validation signoff",
            ],
        },
    }
    if not artifact["acceptance"]["passes"]:
        raise RuntimeError(f"LINX R0 mapping regression failed: {totals}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(artifact, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"output": str(args.output), "totals": totals}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
