#!/usr/bin/env python3
"""Validate the frozen weak/neutron adapter contract without running a solver."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import yaml


EXPECTED_SOLVERS = {"LINX", "PRyMordial", "PRIMAT"}
EXPECTED_SCENARIOS = {"N0", "N1", "N2", "N3"}
EXPECTED_GUARDS = {"D1", "D2", "D3", "D4"}


def load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"YAML root must be a mapping: {path}")
    return payload


def canonical_tau_to_native(
    contract: dict[str, Any], solver_id: str, tau_n_seconds: float
) -> float:
    if not math.isfinite(tau_n_seconds) or tau_n_seconds <= 0:
        raise ValueError("tau_n_seconds must be finite and positive")
    try:
        mapping = contract["solver_mappings"][solver_id]["canonical_to_native"]
    except KeyError as exc:
        raise ValueError(f"unknown solver mapping: {solver_id}") from exc
    kind = mapping["kind"]
    if kind == "ratio_to_frozen_reference":
        reference = float(mapping["reference_tau_n_seconds"])
        if not math.isfinite(reference) or reference <= 0:
            raise ValueError(f"invalid frozen tau_n reference for {solver_id}")
        return tau_n_seconds / reference
    if kind in {"direct_seconds", "direct_seconds_times_solver_unit"}:
        return tau_n_seconds
    raise ValueError(f"unsupported tau_n mapping kind for {solver_id}: {kind!r}")


def validate_contract(contract: dict[str, Any], neutron: dict[str, Any]) -> dict[str, Any]:
    if contract.get("schema_version") != 1 or contract.get("contract_id") != "WEAK-PRIOR-v1":
        raise ValueError("unsupported weak-prior contract")
    if contract.get("task_id") != "UQ0-WEAK-PRIOR":
        raise ValueError("weak-prior contract has the wrong task id")
    if contract.get("scientific_readiness") != "not_ready":
        raise ValueError("unsigned weak-prior contract must not claim scientific readiness")
    if contract.get("production_use") != "prohibited_pending_signoff_and_numerical_regression":
        raise ValueError("unsigned weak-prior contract must prohibit production use")

    variables = contract.get("canonical_variables", {})
    tau = variables.get("tau_n_seconds", {})
    weak_norm = variables.get("weak_theory_normalization", {})
    if tau.get("registry") != "configs/physics/neutron_lifetime_v1.yaml":
        raise ValueError("canonical tau_n must reference NEUTRON-v1")
    if tau.get("primary_scenario") != "N0":
        raise ValueError("canonical tau_n primary scenario must be N0")
    if set(tau.get("mandatory_robustness_scenarios", [])) != {"N1", "N2", "N3"}:
        raise ValueError("canonical tau_n must retain N1-N3 robustness scenarios")
    if weak_norm.get("status") != "fixed_not_sampled_no_reviewed_prior_registered":
        raise ValueError("weak-theory normalization must remain inactive without a prior")

    if neutron.get("prior_id") != "NEUTRON-v1":
        raise ValueError("unexpected neutron-lifetime registry")
    scenarios = neutron.get("scenarios", {})
    if set(scenarios) != EXPECTED_SCENARIOS:
        raise ValueError("NEUTRON-v1 must contain exactly N0-N3")
    if not math.isclose(float(scenarios["N0"]["mean"]), 878.3, rel_tol=0, abs_tol=1e-12):
        raise ValueError("contract expects the frozen N0 mean of 878.3 s")
    if not math.isclose(float(scenarios["N0"]["sigma"]), 0.4, rel_tol=0, abs_tol=1e-12):
        raise ValueError("contract expects the frozen N0 sigma of 0.4 s")

    sampling = contract.get("sampling_contract", {})
    if sampling.get("active_R0_continuous_weak_nuisances") != ["tau_n_seconds"]:
        raise ValueError("tau_n_seconds must be the only active R0 weak nuisance")
    if sampling.get("solver_native_tau_n_sampling") != "disabled":
        raise ValueError("solver-native tau_n sampling must be disabled")
    if sampling.get("weak_theory_normalization_sampling") != "disabled":
        raise ValueError("weak-theory normalization sampling must be disabled")

    mappings = contract.get("solver_mappings", {})
    if set(mappings) != EXPECTED_SOLVERS:
        raise ValueError("weak-prior contract must map LINX, PRyMordial and PRIMAT")
    native_values: dict[str, float] = {}
    for solver_id, mapping in mappings.items():
        revision = mapping.get("revision")
        if not isinstance(revision, str) or len(revision) != 40:
            raise ValueError(f"{solver_id} has no full frozen revision")
        if mapping.get("source_audit_status") != "complete":
            raise ValueError(f"{solver_id} source semantics have not been audited")
        if mapping.get("numerical_regression_status") != "pending_UQ0_NUISANCE_ADAPTER":
            raise ValueError(f"{solver_id} must not claim unexecuted numerical regression")
        evidence = mapping.get("source_evidence")
        if not isinstance(evidence, list) or len(evidence) < 2:
            raise ValueError(f"{solver_id} has insufficient source evidence")
        for item in evidence:
            if not isinstance(item.get("git_blob"), str) or len(item["git_blob"]) != 40:
                raise ValueError(f"{solver_id} source evidence lacks a Git blob")
            if not isinstance(item.get("sha256"), str) or len(item["sha256"]) != 64:
                raise ValueError(f"{solver_id} source evidence lacks SHA256")
        native_values[solver_id] = canonical_tau_to_native(
            contract, solver_id, float(scenarios["N0"]["mean"])
        )

    if not math.isclose(native_values["LINX"], 878.3 / 879.4, rel_tol=0, abs_tol=1e-15):
        raise ValueError("LINX tau_n ratio mapping is inconsistent")
    if native_values["PRyMordial"] != 878.3 or native_values["PRIMAT"] != 878.3:
        raise ValueError("direct-seconds tau_n mappings are inconsistent")

    guard_ids = {
        item.get("id") for item in contract["double_counting_guards"]["forbidden_combinations"]
    }
    if guard_ids != EXPECTED_GUARDS:
        raise ValueError("the four frozen double-counting guards are required")
    state = contract.get("validation_state", {})
    if state.get("A00_scientific_signoff") != "pending":
        raise ValueError("A00 scientific signoff must remain pending")
    if state.get("independent_weak_physics_signoff") != "pending":
        raise ValueError("independent weak-physics signoff must remain pending")
    if state.get("ready_for_production_labels") is not False:
        raise ValueError("contract must not authorize production labels")

    return {
        "contract_id": contract["contract_id"],
        "native_N0_values": native_values,
        "production_use": contract["production_use"],
        "scientific_readiness": contract["scientific_readiness"],
        "solver_count": len(mappings),
        "status": "valid_implementation_contract_not_scientifically_signed",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--neutron-registry", type=Path, required=True)
    args = parser.parse_args()
    report = validate_contract(load_yaml(args.contract), load_yaml(args.neutron_registry))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
