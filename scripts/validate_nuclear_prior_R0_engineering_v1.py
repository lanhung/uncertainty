#!/usr/bin/env python3
"""Validate the executable, non-production Stage-R0 nuclear prior contract."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import yaml


REACTIONS = {"dp_gamma_he3", "dd_n_he3", "dd_p_t"}
PARAMETERS = {"z_dp_gamma_he3", "z_dd_n_he3", "z_dd_p_t"}
PATHS = {"LINX_S6", "PRyMordial_S4", "PRIMAT_S8"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected a mapping in {path}")
    return payload


def validate(prior_path: Path, stage_path: Path, repository_root: Path) -> dict[str, int]:
    prior = load_yaml(prior_path)
    stage = load_yaml(stage_path)

    if prior.get("schema_version") != 1:
        raise ValueError("unsupported engineering-prior schema")
    if prior.get("prior_id") != "NUCLEAR-R0-ENGINEERING-v1":
        raise ValueError("unexpected engineering-prior id")
    if prior.get("status") != ("legacy_solver_envelope_mapping_frozen_ETR25_primary_pending"):
        raise ValueError("legacy solver-envelope mapping must retain pending ETR25 work")
    if prior.get("production_use") != ("prohibited_pending_ETR25_pdf_audit_regression_and_signoff"):
        raise ValueError("engineering prior must prohibit production use")

    coordinate = prior["canonical_coordinate"]
    if set(coordinate["order"]) != PARAMETERS or len(coordinate["order"]) != 3:
        raise ValueError("canonical coordinate must contain exactly three R0 parameters")
    if coordinate.get("covariance_status") != "missing_not_evidence_of_independence":
        raise ValueError("missing cross-reaction covariance is not independence evidence")
    if coordinate.get("covariance_use") != "engineering_baseline_only":
        raise ValueError("identity covariance must be restricted to engineering use")

    package_record = prior["legacy_solver_envelope_package"]
    package_path = repository_root / package_record["path"]
    if sha256(package_path) != package_record["sha256"]:
        raise ValueError("legacy solver-envelope package SHA256 mismatch")
    package = json.loads(package_path.read_text(encoding="utf-8"))
    if package.get("package_id") != package_record["package_id"]:
        raise ValueError("legacy solver-envelope package id mismatch")
    if package["source"]["revision"] != package_record["source_revision"]:
        raise ValueError("legacy solver-envelope package revision mismatch")
    if package["source"]["collection"] != package_record["source_collection"]:
        raise ValueError("legacy solver-envelope package collection mismatch")
    if package["cross_reaction_covariance"]["status"] != ("missing_not_evidence_of_independence"):
        raise ValueError("package overstates cross-reaction covariance")
    if package["functional_posterior_boundary"]["included"] is not False:
        raise ValueError("scalar package cannot claim a functional posterior")

    if set(prior["reactions"]) != REACTIONS or set(package["reactions"]) != REACTIONS:
        raise ValueError("prior and package must contain exactly the three R0 reactions")
    for reaction_id, reaction in prior["reactions"].items():
        if reaction["package_reaction_id"] != reaction_id:
            raise ValueError(f"{reaction_id}: package reaction id mismatch")
        if reaction["source_table_sha256"] != package["reactions"][reaction_id]["source_sha256"]:
            raise ValueError(f"{reaction_id}: source table SHA256 mismatch")

    mappings = prior["solver_mappings"]
    if set(mappings) != PATHS:
        raise ValueError("engineering prior must map exactly the three direct solver paths")
    if mappings["LINX_S6"]["rate_library_relation"] != "exact_legacy_solver_envelope_package":
        raise ValueError("LINX must be the exact legacy-envelope package mapping")
    for path_id in ("PRyMordial_S4", "PRIMAT_S8"):
        if (
            mappings[path_id]["rate_library_relation"]
            != "native_alternative_not_matched_to_legacy_package"
        ):
            raise ValueError(f"{path_id} must remain a native, unmatched rate-library path")
    for path_id, mapping in mappings.items():
        if mapping.get("native_sampling") != "prohibited_use_external_manifest":
            raise ValueError(f"{path_id}: native sampling must be prohibited")
        parameters = mapping["reaction_parameters"]
        if set(parameters) != PARAMETERS:
            raise ValueError(f"{path_id}: canonical parameter mapping is incomplete")

    interpretation = prior["factorial_interpretation"]
    if interpretation.get("common_z_interface_across_three_solvers") is not True:
        raise ValueError("common z interface must be explicit")
    if interpretation.get("matched_rate_library_across_three_solvers") is not False:
        raise ValueError("native solver paths are not matched rate-library paths")
    if interpretation.get("engine_discrepancy_claim_allowed") is not False:
        raise ValueError("unmatched paths cannot support an engine-discrepancy claim")

    if set(prior["signoffs"].values()) != {"pending"}:
        raise ValueError("this engineering contract cannot manufacture scientific sign-offs")
    if prior["regression_gate"].get("status") != "pending":
        raise ValueError("plus/minus regression must remain pending")

    stage_reactions = {item["reaction_id"]: item for item in stage["reactions"]}
    if set(stage_reactions) != REACTIONS:
        raise ValueError("Stage-R0 registry reaction set differs from the engineering prior")
    if stage.get("status") != "public_table_capture_complete_rate_pdf_audit_pending":
        raise ValueError("Stage-R0 registry has an unsafe status")
    if any(item.get("production_enabled") is not False for item in stage_reactions.values()):
        raise ValueError("Stage-R0 production must remain disabled")
    if stage["nuisance_contract"].get("legacy_solver_envelope_mapping_contract") != str(
        prior_path.relative_to(repository_root)
    ):
        raise ValueError("Stage-R0 registry does not bind the legacy envelope mapping")
    if stage["prior_source_policy"].get("primary_candidate") != "ETR25":
        raise ValueError("ETR25 must remain the registered primary candidate")
    if prior["upstream_scientific_gates"].get("common_production_adapter_unlocked") is not False:
        raise ValueError("legacy envelope mapping cannot unlock the production adapter")

    return {
        "canonical_parameters": len(PARAMETERS),
        "mapped_solver_paths": len(PATHS),
        "registered_reactions": len(REACTIONS),
        "pending_signoffs": len(prior["signoffs"]),
        "production_enabled_reactions": sum(
            bool(item["production_enabled"]) for item in stage_reactions.values()
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prior", type=Path, required=True)
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    summary = validate(
        args.prior.resolve(),
        args.stage.resolve(),
        args.repository_root.resolve(),
    )
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
