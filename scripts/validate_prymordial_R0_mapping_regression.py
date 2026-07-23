#!/usr/bin/env python3
"""Validate the frozen PRyMordial R0 mapping-regression artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any


EXPECTED_REVISION = "725d8a8db3ad5ea2630580d825c9d0d69ed76533"
EXPECTED_SOURCE_SHA256 = {
    "PRyM/PRyM_init.py": "7b52cdd4cf7a7c39082d6cdf4a2e4f3b67458dc20d6ff9f07c2b488ef1819e2f",
    "PRyM/PRyM_nuclear_net12.py": "85ffa209d50cf60d1cc5ddad8288ba0237ac39f435c387780a58973327f060d1",
}
EXPECTED_REPOSITORY = "https://github.com/vallima/PRyMordial"
EXPECTED_ENVIRONMENT = {
    "python": "3.11.15",
    "numpy": "2.3.5",
    "scipy": "1.16.3",
    "platform": "Linux-5.15.0-78-generic-x86_64-with-glibc2.35",
}
EXPECTED_TABLES = {
    "dpHe3g": {
        "relative_path": "PRyMrates/nuclear/key_primat_rates/dpHe3g.txt",
        "sha256": "286148ae9b9605e41083937dcc91c2395033b8fb6c9221abcf2f25f860eef347",
        "trace_sha256": "6167449fe44ca2624c0dfb2947569115bd228c4fe697ba355e946e271a6f3e4a",
    },
    "ddHe3n": {
        "relative_path": "PRyMrates/nuclear/key_primat_rates/ddHe3n.txt",
        "sha256": "4804d937668dfb8d9e5eedb8dfd46f39f48306771487625a77ebd26e6d30fbf4",
        "trace_sha256": "ea66791c663a621d9ab69fe47c42c53587d3edd7ff65a577fb9565ce81ea6d92",
    },
    "ddtp": {
        "relative_path": "PRyMrates/nuclear/key_primat_rates/ddtp.txt",
        "sha256": "516038fc7fb4e0b526c7a239efd20437bbeb2f3c5daf734d5d0478320d568790",
        "trace_sha256": "17008bd224af7da3c8a123bed608de39569d5f534b71e31db6d61baa98180b2b",
    },
}
EXPECTED_GRID_SHA256 = "c52c3a340fad83fa852d598dc8f8f7c3a6102b47af6cfeebc4b652d5c549aa20"
EXPECTED_PROBE_SHA256 = "9734ba01853654103b783e25e1ac42f3a19712c0ddd98f4f58dd799c3b995015"
EXPECTED_REACTIONS = {
    "dpHe3g": ("d(p,gamma)3He", 1),
    "ddHe3n": ("d(d,n)3He", 2),
    "ddtp": ("d(d,p)t", 3),
}
EXPECTED_Q = [-3.0, -1.0, 0.0, 1.0, 3.0]


def digest_json(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode(
        "utf-8"
    )
    return hashlib.sha256(payload).hexdigest()


def finite_nonnegative(value: Any) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(value) and value >= 0.0


def validate(path: Path) -> dict[str, int | float | bool]:
    artifact = json.loads(path.read_text(encoding="utf-8"))
    stored_digest = artifact.pop("evidence_sha256")
    if digest_json(artifact) != stored_digest:
        raise ValueError("artifact evidence digest mismatch")
    artifact["evidence_sha256"] = stored_digest

    if artifact["schema_version"] != 1:
        raise ValueError("schema version drift")
    if artifact["artifact_id"] != "PRYMORDIAL-R0-MAPPING-REGRESSION-v1":
        raise ValueError("artifact identity drift")
    if artifact["task_id"] != "UQ0-R0-RATE-PRIOR":
        raise ValueError("task identity drift")
    if artifact["status"] != "non_production_mapping_reverse_numerical_evidence":
        raise ValueError("status overclaim or drift")
    scope = artifact["scientific_scope"]
    required_false = (
        "abundance_level_UQ_run",
        "accepted_scientific_prior",
        "production_authorized",
        "signoff_provided",
    )
    if any(scope[field] is not False for field in required_false):
        raise ValueError("artifact overclaims scientific or production status")
    if scope["claims"] != "C0 numerical mapping regression only":
        raise ValueError("claim level drift")

    source = artifact["source"]
    if source["repository"] != EXPECTED_REPOSITORY:
        raise ValueError("source repository drift")
    if source["revision"] != EXPECTED_REVISION:
        raise ValueError("source revision drift")
    if source["source_sha256"] != EXPECTED_SOURCE_SHA256:
        raise ValueError("source byte provenance drift")
    if source["tracked_worktree_matches_HEAD"] is not True:
        raise ValueError("source tracked worktree provenance drift")
    if source["network"] != "small_net12" or source["rate_collection"] != "key_primat_rates":
        raise ValueError("network or rate collection drift")
    if artifact["environment"] != EXPECTED_ENVIRONMENT:
        raise ValueError("execution environment drift")

    configuration = artifact["configuration"]
    if configuration["q_values"] != EXPECTED_Q:
        raise ValueError("q-probe contract drift")
    if configuration["NP_nuclear_flag"] is not False:
        raise ValueError("NP_nuclear_flag must be false")
    if float(configuration["all_NP_delta"]) != 0.0:
        raise ValueError("native NP deltas must be zero")
    if configuration["floating_point"] != "numpy_float64":
        raise ValueError("floating-point contract drift")
    if configuration["interpolation"] != "scipy_interp1d_linear":
        raise ValueError("interpolation contract drift")
    if configuration["upstream_out_of_grid_behavior"] != "extrapolate":
        raise ValueError("upstream out-of-grid contract drift")
    if configuration["project_out_of_grid_behavior"] != "structured_rejection":
        raise ValueError("project out-of-grid contract drift")

    reactions = artifact["reactions"]
    if len(reactions) != 3 or {item["native_id"] for item in reactions} != set(EXPECTED_REACTIONS):
        raise ValueError("R0 reaction set drift")
    forward_rows = 0
    reverse_defined = 0
    reverse_excluded = 0
    shift_excluded = 0
    max_forward = 0.0
    max_reverse = 0.0
    max_shift = 0.0
    for reaction in reactions:
        canonical, index = EXPECTED_REACTIONS[reaction["native_id"]]
        if reaction["canonical_id"] != canonical:
            raise ValueError("canonical reaction mapping drift")
        if reaction["constructor_parameter"] != f"p_{reaction['native_id']}":
            raise ValueError("native parameter mapping drift")
        if reaction["constructor_index_zero_based"] != index:
            raise ValueError("constructor index drift")
        table = reaction["table"]
        expected_table = EXPECTED_TABLES[reaction["native_id"]]
        if (
            int(table["knot_count"]) != 500
            or float(table["minimum_T9"]) != 0.001
            or float(table["maximum_T9"]) != 10.0
            or table["columns"] != ["T9", "median_forward_rate", "exp_sigma"]
            or table["two_body_forward_rate_unit"] != "cm^3 mol^-1 s^-1"
            or table["relative_path"] != expected_table["relative_path"]
            or table["sha256"] != expected_table["sha256"]
            or table["grid_sha256"] != EXPECTED_GRID_SHA256
        ):
            raise ValueError("native table contract drift")
        probes = reaction["probe_grid"]
        if probes["construction"] != "all_native_knots_plus_geometric_midpoints":
            raise ValueError("probe-grid construction drift")
        if int(probes["count"]) != 999:
            raise ValueError("probe-grid size drift")
        if probes["sha256"] != EXPECTED_PROBE_SHA256:
            raise ValueError("probe-grid provenance drift")
        if reaction["trace_sha256"] != expected_table["trace_sha256"]:
            raise ValueError("rate trace provenance drift")
        q_results = reaction["q_results"]
        if [float(item["q"]) for item in q_results] != EXPECTED_Q:
            raise ValueError("reaction q rows drift")
        for result in q_results:
            for field in (
                "forward_transform_max_relative_error",
                "reverse_over_K_forward_max_relative_error",
                "log_reverse_shift_minus_log_forward_shift_max_abs",
            ):
                if not finite_nonnegative(result[field]):
                    raise ValueError(f"non-finite regression metric: {field}")
            rows = int(result["forward_rows"])
            defined = int(result["reverse_rows_defined"])
            excluded = int(result["reverse_rows_excluded_zero_or_subnormal"])
            if rows != 999 or defined + excluded != rows:
                raise ValueError("reverse underflow accounting is incomplete")
            shift_defined = int(result["log_reverse_shift_minus_log_forward_shift_rows_defined"])
            shift_excluded_count = int(result["log_shift_rows_excluded_zero_or_subnormal"])
            if float(result["q"]) == 0.0:
                if shift_defined != 0 or shift_excluded_count != 0:
                    raise ValueError("q=0 log-shift row accounting drift")
            elif shift_defined + shift_excluded_count != rows:
                raise ValueError("log-shift underflow accounting is incomplete")
            forward_rows += rows
            reverse_defined += defined
            reverse_excluded += excluded
            shift_excluded += shift_excluded_count
            max_forward = max(
                max_forward,
                float(result["forward_transform_max_relative_error"]),
            )
            max_reverse = max(
                max_reverse,
                float(result["reverse_over_K_forward_max_relative_error"]),
            )
            max_shift = max(
                max_shift,
                float(result["log_reverse_shift_minus_log_forward_shift_max_abs"]),
            )

    mapping = artifact["mapping_uniqueness"]
    if mapping["all_three_mappings_unique"] is not True:
        raise ValueError("R0 mapping uniqueness failed")
    if len(mapping["cases"]) != 3:
        raise ValueError("mapping uniqueness case count drift")
    for case in mapping["cases"]:
        if case["unique"] is not True or case["target_changed"] is not True:
            raise ValueError("one-hot mapping case failed")
        if float(case["max_off_target_relative_change"]) != 0.0:
            raise ValueError("one-hot mapping leaked into another R0 rate")

    guard = artifact["duplicate_shift_guard"]
    cases = guard["guard_cases"]
    if len(cases) != 4 or cases[0] != {
        "case": "accepted_external_q_only",
        "accepted": True,
    }:
        raise ValueError("external-q guard acceptance drift")
    if any(case["accepted"] is not False for case in cases[1:]):
        raise ValueError("duplicate-shift guard accepted a prohibited case")
    if any(case["code"] != "duplicate_nuclear_shift_representation" for case in cases[1:]):
        raise ValueError("duplicate-shift rejection is not structured")
    observation = guard["upstream_simultaneous_mechanisms_observation"]
    if observation["accepted_for_project_draws"] is not False:
        raise ValueError("upstream double mechanism was incorrectly accepted")
    if float(observation["max_relative_error_against_native_equation"]) > 2.0e-13:
        raise ValueError("upstream double-mechanism observation drift")

    temperature = artifact["temperature_unit_bounds_contract"]
    if (
        temperature["public_adapter_input_unit"] != "T9"
        or temperature["native_rate_method_input_unit"] != "kelvin"
        or temperature["conversion"] != "kelvin=T9*1e9"
        or temperature["project_policy"] != "structured_rejection_before_solver_call"
    ):
        raise ValueError("temperature/unit contract drift")
    if len(temperature["cases"]) != 21:
        raise ValueError("temperature case count drift")
    for case in temperature["cases"]:
        label = case["case"]
        if label in {"lower_boundary", "upper_boundary"}:
            if case["accepted"] is not True:
                raise ValueError("table boundary was rejected")
        else:
            if case["accepted"] is not False:
                raise ValueError("invalid temperature case was accepted")
            if label != "upstream_direct_out_of_grid_observation" and case["code"] not in {
                "temperature_out_of_bounds",
                "nonfinite_temperature",
                "unsupported_temperature_unit",
            }:
                raise ValueError("temperature rejection is not structured")

    sequential = artifact["sequential_draw_isolation"]
    if sequential["object_lifecycle"] != "fresh_UpdateNuclearRates_instance_per_draw":
        raise ValueError("draw object lifecycle drift")
    if len(sequential["cases"]) != 24:
        raise ValueError("sequential draw case count drift")
    if sequential["consecutive_draw_contamination_observed"] is not False:
        raise ValueError("consecutive draw contamination observed")
    if float(sequential["max_relative_error_against_fresh_reference"]) != 0.0:
        raise ValueError("sequential draws do not reproduce fresh references")

    acceptance = artifact["acceptance"]
    if float(acceptance["relative_tolerance"]) != 5.0e-13:
        raise ValueError("acceptance tolerance drift")
    if float(acceptance["absolute_tolerance"]) != 1.0e-300:
        raise ValueError("absolute acceptance tolerance drift")
    if any(
        acceptance[field] is not True
        for field in (
            "forward_transform_passed",
            "reverse_same_draw_passed",
            "reverse_log_shift_passed",
            "mapping_uniqueness_passed",
            "duplicate_shift_guard_passed",
            "temperature_unit_bounds_contract_passed",
            "sequential_draw_isolation_passed",
        )
    ):
        raise ValueError("one or more acceptance checks failed")
    if max(max_forward, max_reverse, max_shift) > float(acceptance["relative_tolerance"]):
        raise ValueError("numerical regression exceeds acceptance tolerance")

    summary = artifact["summary"]
    recomputed = {
        "reaction_count": 3,
        "q_count": 5,
        "forward_rows": forward_rows,
        "reverse_rows_defined": reverse_defined,
        "reverse_rows_excluded_zero_or_subnormal": reverse_excluded,
        "log_shift_rows_excluded_zero_or_subnormal": shift_excluded,
        "forward_transform_max_relative_error": max_forward,
        "reverse_over_K_forward_max_relative_error": max_reverse,
        "log_reverse_shift_minus_log_forward_shift_max_abs": max_shift,
        "all_three_mappings_unique": True,
        "duplicate_shift_guard_passed": True,
        "sequential_draw_contamination_observed": False,
    }
    for field, value in recomputed.items():
        if summary[field] != value:
            raise ValueError(f"summary drift: {field}")
    if "zero or subnormal" not in summary["underflow_policy"]:
        raise ValueError("underflow exclusion policy is not explicit")
    return recomputed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact", type=Path)
    args = parser.parse_args()
    summary = validate(args.artifact)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
