#!/usr/bin/env python3
"""Validate the self-contained Stage-R0 reference-prior contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import yaml


REACTIONS = ["dp_gamma_he3", "dd_n_he3", "dd_p_t"]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected a YAML mapping in {path}")
    return payload


def resolve(root: Path, path: str) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else root / candidate


def validate(path: Path, repository_root: Path) -> dict[str, Any]:
    record = load_yaml(path)

    if record.get("schema_version") != 1:
        raise ValueError("unsupported R0 reference-prior schema")
    if record.get("prior_id") != "NUCLEAR-R0-REFERENCE-v1":
        raise ValueError("unexpected R0 reference-prior id")
    if record.get("status") != "frozen_for_exploratory_direct_execution":
        raise ValueError("reference-prior status drift")

    boundary = record["claim_boundary"]
    expected_false = [
        "actual_ETR25_functional_posterior_reconstructed",
        "cross_reaction_covariance_inferred",
        "publication_prior_approved",
        "final_cosmological_claim_allowed",
    ]
    for key in expected_false:
        if boundary.get(key) is not False:
            raise ValueError(f"claim boundary is overstated: {key}")
    if boundary.get("exploratory_direct_calculation_allowed") is not True:
        raise ValueError("fast direct calculations are not explicitly authorized")

    for source_id, source in record["source_artifacts"].items():
        if source_id in {"native_baselines", "external_reproduction_audit"}:
            continue
        source_path = resolve(repository_root, source["path"])
        if not source_path.exists():
            raise ValueError(f"missing source artifact: {source_id}")
        if sha256(source_path) != source["sha256"]:
            raise ValueError(f"source artifact SHA256 mismatch: {source_id}")

    native = record["source_artifacts"]["native_baselines"]
    if set(native) != {"PRIMAT", "PRyMordial", "LINX"}:
        raise ValueError("core native baseline set drift")
    for source_id, source_path_value in native.items():
        source_path = resolve(repository_root, source_path_value)
        if not source_path.exists():
            raise ValueError(f"missing native baseline artifact: {source_id}")

    external = record["source_artifacts"]["external_reproduction_audit"]
    if external.get("role") != "non_blocking_negative_or_blocked_evidence":
        raise ValueError("external reproduction audit became a production dependency")
    if not resolve(repository_root, external["path"]).exists():
        raise ValueError("missing external blocker audit")

    if record.get("reaction_order") != REACTIONS:
        raise ValueError("R0 reaction order drift")

    representations = record["representations"]
    expected_representations = {
        "R0_P0_ETR25_scalar_lognormal",
        "R0_P1_ETR25_asymmetric_quantile_rank1",
        "R0_P2_legacy_solver_envelope",
    }
    if set(representations) != expected_representations:
        raise ValueError("R0 representation set drift")
    for representation in representations.values():
        if representation.get("actual_posterior_reconstruction") is not False:
            raise ValueError("reference representation claims actual posterior reconstruction")
        if representation.get("production_truth_claim") != "prohibited":
            raise ValueError("reference representation permits an unqualified truth claim")

    correlation = record["correlation_models"]
    matrix = correlation["baseline"]["matrix"]
    if matrix != [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]:
        raise ValueError("identity engineering anchor drift")
    if correlation["baseline"].get("scientific_independence_claim") is not False:
        raise ValueError("missing covariance was converted into an independence claim")
    if correlation["mandatory_stress_family"].get("model_count") != 35:
        raise ValueError("correlation stress model count drift")

    solver = record["solver_policy"]
    if solver["primary_fast_path"].get("solver") != "LINX":
        raise ValueError("LINX is no longer the primary batched fast path")
    if solver["independent_check"].get("solver") != "PRyMordial":
        raise ValueError("PRyMordial independent-check path drift")
    if solver["precision_native_reference"].get("solver") != "PRIMAT":
        raise ValueError("PRIMAT precision-reference role drift")
    if (
        solver["precision_native_reference"].get(
            "project_ETR25_curve_injection_required_for_fast_path"
        )
        is not False
    ):
        raise ValueError("unresolved PRIMAT curve injection re-entered the fast-path dependency")

    designs = record["fast_designs"]
    if designs["sigma_point_9"].get("total_nodes") is not None:
        raise ValueError("sigma-point node count must remain implied by the frozen rule")
    if designs["gauss_hermite_81"].get("total_nodes") != 81:
        raise ValueError("GH81 design drift")
    if designs["gauss_hermite_refinement"].get("total_nodes") != 625:
        raise ValueError("GH625 refinement drift")
    if designs["qmc_tail_check"].get("common_random_numbers_across_theta") is not True:
        raise ValueError("QMC common-random-number rule was removed")

    grid = record["omega_b_h2_fast_grid"]
    mean = float(grid["source_mean"])
    sigma = float(grid["source_sigma"])
    offsets = [float(item) for item in grid["standardized_offsets"]]
    values = [float(item) for item in grid["values"]]
    expected_values = [mean + offset * sigma for offset in offsets]
    if any(not math.isclose(a, b, rel_tol=0.0, abs_tol=1e-12) for a, b in zip(values, expected_values)):
        raise ValueError("omega_b_h2 fast-grid arithmetic drift")

    upgrade = record["publication_upgrade"]
    if upgrade.get("external_atlas_or_GP_exact_rerun_required") is not False:
        raise ValueError("unpublished external artifacts re-entered the publication dependency")
    if upgrade.get("external_atlas_or_GP_status_must_be_disclosed") is not True:
        raise ValueError("external blocker disclosure was removed")

    return {
        "prior_id": record["prior_id"],
        "reactions": len(REACTIONS),
        "representations": len(representations),
        "correlation_models": correlation["mandatory_stress_family"]["model_count"],
        "GH81_nodes": designs["gauss_hermite_81"]["total_nodes"],
        "omega_b_h2_points": len(values),
        "exploratory_direct_calculation_allowed": boundary[
            "exploratory_direct_calculation_allowed"
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/physics/nuclear_prior_R0_reference_v1.yaml"),
    )
    parser.add_argument("--repository-root", type=Path, default=Path("."))
    args = parser.parse_args()
    summary = validate(args.config, args.repository_root.resolve())
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
