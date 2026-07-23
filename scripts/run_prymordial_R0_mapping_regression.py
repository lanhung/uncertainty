#!/usr/bin/env python3
"""Run the frozen PRyMordial R0 rate-mapping regression.

This is deliberately a rate-level, non-production diagnostic.  It does not
integrate the abundance ODEs and it does not approve a scientific prior.
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
from dataclasses import dataclass
from pathlib import Path
from typing import Any


EXPECTED_REVISION = "725d8a8db3ad5ea2630580d825c9d0d69ed76533"
EXPECTED_SOURCE_SHA256 = {
    "PRyM/PRyM_init.py": "7b52cdd4cf7a7c39082d6cdf4a2e4f3b67458dc20d6ff9f07c2b488ef1819e2f",
    "PRyM/PRyM_nuclear_net12.py": "85ffa209d50cf60d1cc5ddad8288ba0237ac39f435c387780a58973327f060d1",
}
Q_PROBES = (-3.0, -1.0, 0.0, 1.0, 3.0)
RELATIVE_TOLERANCE = 5.0e-13
ABSOLUTE_TOLERANCE = 1.0e-300
np: Any = None


@dataclass(frozen=True)
class Reaction:
    canonical_id: str
    native_id: str
    constructor_index: int
    table_sha256: str


REACTIONS = (
    Reaction(
        "d(p,gamma)3He",
        "dpHe3g",
        1,
        "286148ae9b9605e41083937dcc91c2395033b8fb6c9221abcf2f25f860eef347",
    ),
    Reaction(
        "d(d,n)3He",
        "ddHe3n",
        2,
        "4804d937668dfb8d9e5eedb8dfd46f39f48306771487625a77ebd26e6d30fbf4",
    ),
    Reaction(
        "d(d,p)t",
        "ddtp",
        3,
        "516038fc7fb4e0b526c7a239efd20437bbeb2f3c5daf734d5d0478320d568790",
    ),
)


class MappingContractError(ValueError):
    """Structured rejection at the project adapter boundary."""

    def __init__(self, code: str, **details: Any) -> None:
        self.code = code
        self.details = details
        super().__init__(f"{code}: {details}")

    def as_record(self) -> dict[str, Any]:
        return {"accepted": False, "code": self.code, "details": self.details}


def require_numpy() -> Any:
    """Load NumPy only for the worker runner, not adapter-contract unit tests."""
    global np
    if np is None:
        import numpy as numpy_module

        np = numpy_module
    return np


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest_json(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode(
        "utf-8"
    )
    return hashlib.sha256(payload).hexdigest()


def git_revision(root: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def tracked_worktree_matches_head(root: Path) -> bool:
    return (
        subprocess.run(
            ["git", "diff", "--quiet", "HEAD", "--", "."],
            cwd=root,
            check=False,
        ).returncode
        == 0
    )


def validate_temperature(
    reaction: str,
    value: float,
    *,
    unit: str,
    minimum_t9: float,
    maximum_t9: float,
) -> float:
    """Validate a public adapter temperature and convert T9 to kelvin."""
    if unit != "T9":
        raise MappingContractError(
            "unsupported_temperature_unit",
            reaction=reaction,
            supplied_unit=unit,
            required_unit="T9",
        )
    if not math.isfinite(value):
        raise MappingContractError(
            "nonfinite_temperature",
            reaction=reaction,
            supplied_value=str(value),
            unit=unit,
        )
    if value < minimum_t9 or value > maximum_t9:
        raise MappingContractError(
            "temperature_out_of_bounds",
            reaction=reaction,
            supplied_value=value,
            unit=unit,
            minimum_t9=minimum_t9,
            maximum_t9=maximum_t9,
        )
    return value * 1.0e9


def validate_external_draw_contract(
    *,
    np_nuclear_flag: bool,
    deltas: dict[str, float],
) -> None:
    """Require exactly one uncertainty representation for a project draw."""
    nonzero = {
        key: value
        for key, value in deltas.items()
        if not math.isclose(float(value), 0.0, rel_tol=0.0, abs_tol=0.0)
    }
    if np_nuclear_flag or nonzero:
        raise MappingContractError(
            "duplicate_nuclear_shift_representation",
            np_nuclear_flag=np_nuclear_flag,
            nonzero_native_deltas=nonzero,
            required="NP_nuclear_flag_false_and_all_NP_delta_zero",
        )


def relative_error(value: float, expected: float) -> float:
    if expected == 0.0:
        return 0.0 if value == 0.0 else math.inf
    return abs(value / expected - 1.0)


def load_frozen_source(source_root: Path) -> tuple[Any, Any]:
    revision = git_revision(source_root)
    if revision != EXPECTED_REVISION:
        raise RuntimeError(f"PRyMordial revision drift: {revision} != {EXPECTED_REVISION}")
    for relative, expected in EXPECTED_SOURCE_SHA256.items():
        actual = sha256(source_root / relative)
        if actual != expected:
            raise RuntimeError(f"source byte drift for {relative}: {actual}")

    old_cwd = Path.cwd()
    sys.path.insert(0, str(source_root))
    os.chdir(source_root)
    try:
        import PRyM.PRyM_init as init  # type: ignore[import-not-found]
        import PRyM.PRyM_nuclear_net12 as net12  # type: ignore[import-not-found]
    finally:
        os.chdir(old_cwd)
    return init, net12


def constructor_args(reaction: Reaction | None = None, q: float = 0.0) -> list[float]:
    args = [0.0] * 12
    if reaction is not None:
        args[reaction.constructor_index] = q
    return args


def reaction_arrays(init: Any, reaction: Reaction) -> tuple[np.ndarray, ...]:
    return tuple(
        np.asarray(getattr(init, f"{reaction.native_id}_{suffix}"), dtype=np.float64)
        for suffix in ("T9", "median", "expsigma")
    )


def probe_grid(knots: np.ndarray) -> np.ndarray:
    midpoints = np.sqrt(knots[:-1] * knots[1:])
    return np.sort(np.concatenate((knots, midpoints)))


def evaluate_rate(net: Any, reaction: Reaction, t9: float) -> tuple[float, float]:
    kelvin = t9 * 1.0e9
    forward = float(getattr(net, f"{reaction.native_id}_frwrd")(kelvin))
    reverse = float(getattr(net, f"{reaction.native_id}_bkwrd")(kelvin))
    return forward, reverse


def trace_row(
    reaction: Reaction,
    q: float,
    t9: float,
    forward: float,
    reverse: float,
) -> list[str]:
    return [
        reaction.native_id,
        format(q, ".17g"),
        format(t9, ".17g"),
        format(forward, ".17g"),
        format(reverse, ".17g"),
    ]


def audit_reaction(init: Any, net12: Any, reaction: Reaction) -> dict[str, Any]:
    knots, medians, exp_sigmas = reaction_arrays(init, reaction)
    table_path = (
        Path(init.working_dir)
        / "PRyMrates"
        / "nuclear"
        / "key_primat_rates"
        / f"{reaction.native_id}.txt"
    )
    if sha256(table_path) != reaction.table_sha256:
        raise RuntimeError(f"table byte drift for {reaction.native_id}")
    if not (
        len(knots) == len(medians) == len(exp_sigmas)
        and len(knots) >= 2
        and np.all(np.diff(knots) > 0.0)
        and np.all(medians > 0.0)
        and np.all(exp_sigmas > 0.0)
    ):
        raise RuntimeError(f"invalid table for {reaction.native_id}")

    probes = probe_grid(knots)
    alpha = float(getattr(init, f"alpha_{reaction.native_id}"))
    beta = float(getattr(init, f"beta_{reaction.native_id}"))
    gamma = float(getattr(init, f"gamma_{reaction.native_id}"))
    q_results: list[dict[str, Any]] = []
    trace: list[list[str]] = []
    baseline_forward: dict[float, float] = {}
    baseline_reverse: dict[float, float] = {}

    for q in Q_PROBES:
        net = net12.UpdateNuclearRates(*constructor_args(reaction, q))
        perturbed_knots = medians * np.exp(q * np.log(exp_sigmas))
        max_forward_error = 0.0
        max_reverse_error = 0.0
        max_log_shift_error = 0.0
        defined_reverse = 0
        excluded_reverse = 0
        defined_shift = 0
        excluded_shift = 0
        for t9 in probes:
            t9_value = float(t9)
            forward, reverse = evaluate_rate(net, reaction, t9_value)
            expected_forward = float(np.interp(t9_value, knots, perturbed_knots))
            max_forward_error = max(max_forward_error, relative_error(forward, expected_forward))
            balance = alpha * t9_value**beta * math.exp(gamma / t9_value)
            expected_reverse = balance * forward
            reverse_defined = (
                math.isfinite(expected_reverse)
                and math.isfinite(reverse)
                and expected_reverse >= sys.float_info.min
                and reverse >= sys.float_info.min
            )
            if reverse_defined:
                defined_reverse += 1
                max_reverse_error = max(
                    max_reverse_error, relative_error(reverse, expected_reverse)
                )
            else:
                excluded_reverse += 1

            if q == 0.0:
                baseline_forward[t9_value] = forward
                baseline_reverse[t9_value] = reverse
            else:
                base_forward = baseline_forward.get(t9_value)
                base_reverse = baseline_reverse.get(t9_value)
                shift_defined = (
                    base_forward is not None
                    and base_reverse is not None
                    and forward >= sys.float_info.min
                    and reverse >= sys.float_info.min
                    and base_forward >= sys.float_info.min
                    and base_reverse >= sys.float_info.min
                )
                if shift_defined:
                    defined_shift += 1
                    shift_error = abs(
                        (math.log(reverse) - math.log(base_reverse))
                        - (math.log(forward) - math.log(base_forward))
                    )
                    max_log_shift_error = max(max_log_shift_error, shift_error)
                else:
                    excluded_shift += 1
            trace.append(trace_row(reaction, q, t9_value, forward, reverse))

        q_results.append(
            {
                "q": q,
                "forward_rows": len(probes),
                "forward_transform_max_relative_error": max_forward_error,
                "reverse_rows_defined": defined_reverse,
                "reverse_rows_excluded_zero_or_subnormal": excluded_reverse,
                "reverse_over_K_forward_max_relative_error": max_reverse_error,
                "log_reverse_shift_minus_log_forward_shift_rows_defined": (defined_shift),
                "log_shift_rows_excluded_zero_or_subnormal": excluded_shift,
                "log_reverse_shift_minus_log_forward_shift_max_abs": (max_log_shift_error),
            }
        )

    # The q loop above encounters q=0 after negative probes.  Recompute shift
    # metrics now that the baseline exists for all temperatures.
    for q_record in q_results:
        q = float(q_record["q"])
        if q == 0.0:
            continue
        net = net12.UpdateNuclearRates(*constructor_args(reaction, q))
        defined = 0
        excluded = 0
        maximum = 0.0
        for t9 in probes:
            t9_value = float(t9)
            forward, reverse = evaluate_rate(net, reaction, t9_value)
            base_forward = baseline_forward[t9_value]
            base_reverse = baseline_reverse[t9_value]
            if (
                forward >= sys.float_info.min
                and reverse >= sys.float_info.min
                and base_forward >= sys.float_info.min
                and base_reverse >= sys.float_info.min
            ):
                defined += 1
                maximum = max(
                    maximum,
                    abs(
                        (math.log(reverse) - math.log(base_reverse))
                        - (math.log(forward) - math.log(base_forward))
                    ),
                )
            else:
                excluded += 1
        q_record["log_reverse_shift_minus_log_forward_shift_rows_defined"] = defined
        q_record["log_shift_rows_excluded_zero_or_subnormal"] = excluded
        q_record["log_reverse_shift_minus_log_forward_shift_max_abs"] = maximum

    return {
        "canonical_id": reaction.canonical_id,
        "native_id": reaction.native_id,
        "constructor_parameter": f"p_{reaction.native_id}",
        "constructor_index_zero_based": reaction.constructor_index,
        "table": {
            "relative_path": (f"PRyMrates/nuclear/key_primat_rates/{reaction.native_id}.txt"),
            "sha256": reaction.table_sha256,
            "columns": ["T9", "median_forward_rate", "exp_sigma"],
            "two_body_forward_rate_unit": "cm^3 mol^-1 s^-1",
            "knot_count": len(knots),
            "minimum_T9": float(knots[0]),
            "maximum_T9": float(knots[-1]),
            "grid_sha256": digest_json([float(value) for value in knots]),
        },
        "probe_grid": {
            "construction": "all_native_knots_plus_geometric_midpoints",
            "count": len(probes),
            "sha256": digest_json([float(value) for value in probes]),
        },
        "detailed_balance": {
            "equation": "reverse=alpha*T9**beta*exp(gamma/T9)*same_forward_spline",
            "alpha": alpha,
            "beta": beta,
            "gamma": gamma,
        },
        "q_results": q_results,
        "trace_sha256": digest_json(trace),
    }


def audit_mapping_uniqueness(init: Any, net12: Any) -> dict[str, Any]:
    baseline = net12.UpdateNuclearRates(*constructor_args())
    cases: list[dict[str, Any]] = []
    for target in REACTIONS:
        perturbed = net12.UpdateNuclearRates(*constructor_args(target, 1.0))
        target_changed = False
        max_off_target_relative_change = 0.0
        response_by_reaction: dict[str, float] = {}
        for observed in REACTIONS:
            knots, _, _ = reaction_arrays(init, observed)
            probes = probe_grid(knots)
            maximum = 0.0
            for t9 in probes:
                base_forward, _ = evaluate_rate(baseline, observed, float(t9))
                shifted_forward, _ = evaluate_rate(perturbed, observed, float(t9))
                maximum = max(maximum, relative_error(shifted_forward, base_forward))
            response_by_reaction[observed.native_id] = maximum
            if observed == target:
                target_changed = maximum > 0.0
            else:
                max_off_target_relative_change = max(max_off_target_relative_change, maximum)
        cases.append(
            {
                "target_parameter": f"p_{target.native_id}",
                "constructor_index_zero_based": target.constructor_index,
                "response_max_relative_change": response_by_reaction,
                "target_changed": target_changed,
                "max_off_target_relative_change": max_off_target_relative_change,
                "unique": target_changed and max_off_target_relative_change <= RELATIVE_TOLERANCE,
            }
        )
    return {
        "cases": cases,
        "all_three_mappings_unique": all(case["unique"] for case in cases),
    }


def audit_np_guard(init: Any, net12: Any) -> dict[str, Any]:
    delta_names = [f"NP_delta_{reaction.native_id}" for reaction in REACTIONS]
    saved_flag = bool(init.NP_nuclear_flag)
    saved_deltas = {name: float(getattr(init, name)) for name in delta_names}
    guard_cases: list[dict[str, Any]] = []
    try:
        for label, flag, deltas in (
            ("accepted_external_q_only", False, {name: 0.0 for name in delta_names}),
            ("reject_flag_even_zero_delta", True, {name: 0.0 for name in delta_names}),
            (
                "reject_latent_nonzero_delta",
                False,
                {delta_names[0]: 0.25, delta_names[1]: 0.0, delta_names[2]: 0.0},
            ),
            (
                "reject_simultaneous_q_and_delta",
                True,
                {delta_names[0]: 0.25, delta_names[1]: 0.0, delta_names[2]: 0.0},
            ),
        ):
            try:
                validate_external_draw_contract(np_nuclear_flag=flag, deltas=deltas)
                guard_cases.append({"case": label, "accepted": True})
            except MappingContractError as error:
                guard_cases.append({"case": label, **error.as_record()})

        # Observe the upstream additive second mechanism, without accepting it.
        target = REACTIONS[0]
        init.NP_nuclear_flag = True
        for name in delta_names:
            setattr(init, name, 0.25 if name == f"NP_delta_{target.native_id}" else 0.0)
        net = net12.UpdateNuclearRates(*constructor_args(target, 1.0))
        knots, medians, exp_sigmas = reaction_arrays(init, target)
        maximum = 0.0
        for index, t9 in enumerate(knots):
            actual, _ = evaluate_rate(net, target, float(t9))
            expected = float(
                medians[index] * math.exp(math.log(exp_sigmas[index])) + 0.25 * medians[index]
            )
            maximum = max(maximum, relative_error(actual, expected))
    finally:
        init.NP_nuclear_flag = saved_flag
        for name, value in saved_deltas.items():
            setattr(init, name, value)

    return {
        "accepted_contract": ("NP_nuclear_flag=False and every NP_delta_* exactly zero"),
        "guard_cases": guard_cases,
        "upstream_simultaneous_mechanisms_observation": {
            "reaction": REACTIONS[0].native_id,
            "q": 1.0,
            "NP_delta": 0.25,
            "native_equation": ("median*exp(q*log(exp_sigma))+NP_delta*median"),
            "max_relative_error_against_native_equation": maximum,
            "accepted_for_project_draws": False,
        },
    }


def audit_temperature_contract(init: Any, net12: Any) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for reaction in REACTIONS:
        knots, _, _ = reaction_arrays(init, reaction)
        low = float(knots[0])
        high = float(knots[-1])
        for label, value, unit in (
            ("lower_boundary", low, "T9"),
            ("upper_boundary", high, "T9"),
            ("below_lower_boundary", math.nextafter(low, -math.inf), "T9"),
            ("above_upper_boundary", math.nextafter(high, math.inf), "T9"),
            ("nonfinite_nan", math.nan, "T9"),
            ("wrong_unit_kelvin", low * 1.0e9, "K"),
        ):
            try:
                kelvin = validate_temperature(
                    reaction.native_id,
                    value,
                    unit=unit,
                    minimum_t9=low,
                    maximum_t9=high,
                )
                records.append(
                    {
                        "reaction": reaction.native_id,
                        "case": label,
                        "accepted": True,
                        "input_value": value,
                        "input_unit": unit,
                        "converted_kelvin": kelvin,
                    }
                )
            except MappingContractError as error:
                records.append(
                    {
                        "reaction": reaction.native_id,
                        "case": label,
                        "input_value": str(value) if not math.isfinite(value) else value,
                        "input_unit": unit,
                        **error.as_record(),
                    }
                )

        # Document, but do not accept, the upstream scipy extrapolation.
        upstream = net12.UpdateNuclearRates(*constructor_args())
        below = low * 0.9
        above = high * 1.1
        below_value, _ = evaluate_rate(upstream, reaction, below)
        above_value, _ = evaluate_rate(upstream, reaction, above)
        records.append(
            {
                "reaction": reaction.native_id,
                "case": "upstream_direct_out_of_grid_observation",
                "accepted": False,
                "project_rejection_code": "temperature_out_of_bounds",
                "upstream_behavior": "linear_extrapolation_without_exception",
                "finite_below": math.isfinite(below_value),
                "finite_above": math.isfinite(above_value),
            }
        )
    return {
        "public_adapter_input_unit": "T9",
        "native_rate_method_input_unit": "kelvin",
        "conversion": "kelvin=T9*1e9",
        "upstream_bounds_error": False,
        "upstream_fill_value": "extrapolate",
        "project_policy": "structured_rejection_before_solver_call",
        "cases": records,
    }


def audit_sequential_draws(init: Any, net12: Any) -> dict[str, Any]:
    sequence = (-3.0, 3.0, -1.0, 1.0, 0.0, -3.0, 0.0, 3.0)
    cases: list[dict[str, Any]] = []
    maximum = 0.0
    for reaction in REACTIONS:
        knots, _, _ = reaction_arrays(init, reaction)
        probes = probe_grid(knots)
        reference: dict[float, list[float]] = {}
        for q in set(sequence):
            net = net12.UpdateNuclearRates(*constructor_args(reaction, q))
            reference[q] = [evaluate_rate(net, reaction, float(t9))[0] for t9 in probes]
        for draw_index, q in enumerate(sequence):
            net = net12.UpdateNuclearRates(*constructor_args(reaction, q))
            actual = [evaluate_rate(net, reaction, float(t9))[0] for t9 in probes]
            error = max(
                relative_error(value, expected) for value, expected in zip(actual, reference[q])
            )
            maximum = max(maximum, error)
            cases.append(
                {
                    "reaction": reaction.native_id,
                    "draw_index": draw_index,
                    "q": q,
                    "max_relative_error_against_fresh_reference": error,
                }
            )
    return {
        "object_lifecycle": "fresh_UpdateNuclearRates_instance_per_draw",
        "sequence": list(sequence),
        "cases": cases,
        "max_relative_error_against_fresh_reference": maximum,
        "consecutive_draw_contamination_observed": maximum > RELATIVE_TOLERANCE,
    }


def build_artifact(source_root: Path) -> dict[str, Any]:
    require_numpy()
    if not tracked_worktree_matches_head(source_root):
        raise RuntimeError("PRyMordial tracked worktree differs from frozen HEAD")
    init, net12 = load_frozen_source(source_root)
    if bool(init.nacreii_flag):
        raise RuntimeError("frozen diagnostic requires key_primat_rates")
    if bool(init.NP_nuclear_flag):
        raise RuntimeError("frozen diagnostic requires NP_nuclear_flag=False")

    reaction_results = [audit_reaction(init, net12, reaction) for reaction in REACTIONS]
    mapping = audit_mapping_uniqueness(init, net12)
    np_guard = audit_np_guard(init, net12)
    temperature = audit_temperature_contract(init, net12)
    sequential = audit_sequential_draws(init, net12)

    all_forward = [
        float(result["forward_transform_max_relative_error"])
        for reaction in reaction_results
        for result in reaction["q_results"]
    ]
    all_reverse = [
        float(result["reverse_over_K_forward_max_relative_error"])
        for reaction in reaction_results
        for result in reaction["q_results"]
    ]
    all_shifts = [
        float(result["log_reverse_shift_minus_log_forward_shift_max_abs"])
        for reaction in reaction_results
        for result in reaction["q_results"]
    ]
    underflow_reverse = sum(
        int(result["reverse_rows_excluded_zero_or_subnormal"])
        for reaction in reaction_results
        for result in reaction["q_results"]
    )
    underflow_shift = sum(
        int(result["log_shift_rows_excluded_zero_or_subnormal"])
        for reaction in reaction_results
        for result in reaction["q_results"]
    )

    artifact = {
        "schema_version": 1,
        "artifact_id": "PRYMORDIAL-R0-MAPPING-REGRESSION-v1",
        "task_id": "UQ0-R0-RATE-PRIOR",
        "status": "non_production_mapping_reverse_numerical_evidence",
        "scientific_scope": {
            "abundance_level_UQ_run": False,
            "accepted_scientific_prior": False,
            "production_authorized": False,
            "signoff_provided": False,
            "claims": "C0 numerical mapping regression only",
        },
        "source": {
            "repository": "https://github.com/vallima/PRyMordial",
            "revision": EXPECTED_REVISION,
            "network": "small_net12",
            "rate_collection": "key_primat_rates",
            "source_sha256": EXPECTED_SOURCE_SHA256,
            "tracked_worktree_matches_HEAD": True,
        },
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": importlib.metadata.version("scipy"),
            "platform": platform.platform(),
        },
        "configuration": {
            "q_values": list(Q_PROBES),
            "NP_nuclear_flag": False,
            "all_NP_delta": 0.0,
            "interpolation": "scipy_interp1d_linear",
            "upstream_out_of_grid_behavior": "extrapolate",
            "project_out_of_grid_behavior": "structured_rejection",
            "floating_point": "numpy_float64",
        },
        "reactions": reaction_results,
        "mapping_uniqueness": mapping,
        "duplicate_shift_guard": np_guard,
        "temperature_unit_bounds_contract": temperature,
        "sequential_draw_isolation": sequential,
        "summary": {
            "reaction_count": len(reaction_results),
            "q_count": len(Q_PROBES),
            "forward_rows": sum(
                int(result["forward_rows"])
                for reaction in reaction_results
                for result in reaction["q_results"]
            ),
            "reverse_rows_defined": sum(
                int(result["reverse_rows_defined"])
                for reaction in reaction_results
                for result in reaction["q_results"]
            ),
            "reverse_rows_excluded_zero_or_subnormal": underflow_reverse,
            "log_shift_rows_excluded_zero_or_subnormal": underflow_shift,
            "forward_transform_max_relative_error": max(all_forward),
            "reverse_over_K_forward_max_relative_error": max(all_reverse),
            "log_reverse_shift_minus_log_forward_shift_max_abs": max(all_shifts),
            "all_three_mappings_unique": mapping["all_three_mappings_unique"],
            "duplicate_shift_guard_passed": (
                np_guard["guard_cases"][0]["accepted"] is True
                and all(case["accepted"] is False for case in np_guard["guard_cases"][1:])
            ),
            "sequential_draw_contamination_observed": sequential[
                "consecutive_draw_contamination_observed"
            ],
            "underflow_policy": (
                "only zero or subnormal reverse values are excluded from "
                "ratio/log identities and every exclusion is counted"
            ),
        },
        "acceptance": {
            "relative_tolerance": RELATIVE_TOLERANCE,
            "absolute_tolerance": ABSOLUTE_TOLERANCE,
            "forward_transform_passed": max(all_forward) <= RELATIVE_TOLERANCE,
            "reverse_same_draw_passed": max(all_reverse) <= RELATIVE_TOLERANCE,
            "reverse_log_shift_passed": max(all_shifts) <= RELATIVE_TOLERANCE,
            "mapping_uniqueness_passed": mapping["all_three_mappings_unique"],
            "duplicate_shift_guard_passed": (
                np_guard["guard_cases"][0]["accepted"] is True
                and all(case["accepted"] is False for case in np_guard["guard_cases"][1:])
            ),
            "temperature_unit_bounds_contract_passed": all(
                (
                    case["accepted"] is True
                    if case["case"] in {"lower_boundary", "upper_boundary"}
                    else case["accepted"] is False
                )
                for case in temperature["cases"]
            ),
            "sequential_draw_isolation_passed": not sequential[
                "consecutive_draw_contamination_observed"
            ],
        },
    }
    artifact["evidence_sha256"] = digest_json(artifact)
    return artifact


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    artifact = build_artifact(args.source_root.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(artifact, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(artifact["summary"], indent=2, sort_keys=True))
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
