#!/usr/bin/env python3
"""Validate the fail-closed GP deuterium-prior structure artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


EXPECTED_ARCHIVE = "1123d5327c48fd57c55626cbb804854b5c3832443f1f49dd3c04626ae97cd04d"
EXPECTED_TEX = "36bc00fba6626b5394b8820868325e0df8d2f7ee40899eb692dc9da0e161ab97"
EXPECTED_REACTIONS = {"ddn", "ddp", "dpg"}


def digest_json(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def validate(path: Path) -> dict[str, Any]:
    artifact = json.loads(path.read_text(encoding="utf-8"))
    stored = artifact.pop("evidence_sha256")
    if digest_json(artifact) != stored:
        raise ValueError("artifact evidence digest mismatch")
    artifact["evidence_sha256"] = stored
    if (
        artifact["schema_version"] != 1
        or artifact["artifact_id"] != "GP-DEUTERIUM-PRIOR-STRUCTURE-v1"
        or artifact["task_id"] != "UQ0-NATIVE-UQ-REPRO"
        or artifact["status"] != "public_structure_captured_abundance_rerun_blocked"
    ):
        raise ValueError("artifact identity/status drift")
    source = artifact["source"]
    if (
        source["arxiv"] != "2604.16600v1"
        or source["observed_source_archive_sha256"] != EXPECTED_ARCHIVE
        or source["observed_tex_sha256"] != EXPECTED_TEX
    ):
        raise ValueError("source provenance drift")
    if not all(artifact["required_tex_markers"].values()):
        raise ValueError("paper structure capture incomplete")
    structure = artifact["prior_structure"]
    if set(structure["reactions"]) != EXPECTED_REACTIONS:
        raise ValueError("reaction set drift")
    if structure["reactions"]["dpg"]["latent_space"] != "log_S_factor":
        raise ValueError("d(p,gamma)3He latent-space drift")
    if (
        structure["kernel"]["combination"] != "additive"
        or structure["kernel"]["global"] != "squared_exponential"
        or structure["kernel"]["local"] != "Matern_nu_1_over_4"
        or structure["kernel"]["fit_method"] != "leave_dataset_out_predictive_pseudolikelihood"
    ):
        raise ValueError("kernel/fit structure drift")
    if structure["draw_contract"]["independent_temperature_bin_noise"] != "prohibited":
        raise ValueError("coherent-draw contract drift")
    unavailable = artifact["reproduction_inputs_unavailable"]
    if set(unavailable) != {
        "analysis_code",
        "fitted_hyperparameters",
        "posterior_draws",
        "experimental_data_bundle",
        "random_seed",
    } or not all(unavailable.values()):
        raise ValueError("fail-closed availability accounting drift")
    scope = artifact["scientific_scope"]
    if (
        scope["exact_abundance_distribution_reproduced"] is not False
        or scope["native_UQ_task_progress_eligible"] is not False
        or scope["accepted_project_prior"] is not False
        or scope["production_authorized"] is not False
        or scope["novelty_claim"] is not False
    ):
        raise ValueError("GP audit overclaims scientific completion")
    abundance = artifact["published_abundance_references"]
    if (
        abundance["fixed_Planck_central_omega_b"]["draws"] != 60000
        or abundance["Planck_omega_b_marginalized"]["draws"] != 100000
        or abundance["Planck_omega_b_marginalized"]["1e5_D_over_H_mean"] != 2.442
        or abundance["Planck_omega_b_marginalized"]["1e5_D_over_H_sigma"] != 0.040
    ):
        raise ValueError("published abundance reference drift")
    return {
        "structure_capture_accepted": True,
        "native_UQ_task_progress_eligible": False,
        "reaction_count": len(structure["reactions"]),
        "missing_reproduction_input_count": len(unavailable),
        "evidence_sha256": stored,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact", type=Path)
    args = parser.parse_args()
    print(json.dumps(validate(args.artifact), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
