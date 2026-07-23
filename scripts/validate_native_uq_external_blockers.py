#!/usr/bin/env python3
"""Validate the fail-closed audit for the two external native-UQ blockers."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


EXPECTED_ACCEPTED = ["PRIMAT", "PRyMordial", "LINX-v2"]
EXPECTED_ATLAS_FAILURES = [
    "central_reference_mismatch:ddHe3n:Li7H",
    "central_reference_mismatch:ddtp:Li7H",
    "central_reference_mismatch:dpHe3g:Li7H",
    "derivative_sign_mismatch:dpHe3g:Yp",
]
EXPECTED_BLOCKED_GP_INPUTS = [
    "analysis_code",
    "fitted_hyperparameters",
    "exact_experimental_data_bundle",
    "posterior_draws",
    "random_seed",
]
EXPECTED_CHANGED_PATH = "PRyMrates/nuclear/key_nacreii_rates/dpHe3g.txt"
EXPECTED_SOLVER_HASHES = {
    "PRyM/PRyM_init.py": "7b52cdd4cf7a7c39082d6cdf4a2e4f3b67458dc20d6ff9f07c2b488ef1819e2f",
    "PRyM/PRyM_main.py": "98f0724f27ace2927d38c3eec615def05bfbfd9c1c9cc09cfa91470417b3451f",
    "PRyM/PRyM_nuclear_net63.py": "dfc634de131e740810f3e2992649f82747173495b2c8e6e0f849a69b1f6da577",
}


def digest_json(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate(
    audit_path: Path,
    atlas_artifact_path: Path,
    gp_artifact_path: Path,
) -> dict[str, Any]:
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    require(audit.get("schema_version") == 1, "audit schema drift")
    require(
        audit.get("artifact_id") == "NATIVE-UQ-EXTERNAL-BLOCKERS-v1",
        "audit identity drift",
    )
    require(audit.get("task_id") == "UQ0-NATIVE-UQ-REPRO", "task identity drift")

    boundary = audit["scientific_boundary"]
    require(boundary["acceptance_thresholds_changed"] is False, "threshold drift")
    require(boundary["native_uq_task_progress_eligible"] is False, "progress overclaim")
    require(boundary["production_authorized"] is False, "production overclaim")
    require(boundary["novelty_claim"] is False, "novelty overclaim")

    progress = audit["native_uq_task_progress"]
    require(progress["accepted_baselines"] == EXPECTED_ACCEPTED, "accepted baseline drift")
    require(progress["before_audit"] == progress["after_audit"] == 3, "progress drift")
    require(progress["total"] == 5, "task total drift")
    require(progress["production_authorized"] is False, "task production overclaim")

    atlas = audit["sensitivity_atlas"]
    require(atlas["status"] == "externally_blocked", "atlas status drift")
    require(
        atlas["atlas_repository"]["generator_revision_declared"] is False,
        "atlas generator state changed",
    )
    require(
        atlas["atlas_repository"]["generator_candidate_extension_count"] == 0,
        "atlas generator candidate count drift",
    )
    comparison = atlas["prymordial_revision_audit"]["comparison"]
    require(comparison["ahead_by"] == 2, "PRyMordial comparison count drift")
    require(comparison["changed_paths"] == [EXPECTED_CHANGED_PATH], "changed path drift")
    require("NACRE-II" in comparison["relevance_to_registered_atlas_path"], "rate path drift")
    require(
        atlas["prymordial_revision_audit"]["solver_source_hashes_identical"]
        == EXPECTED_SOLVER_HASHES,
        "solver source hash audit drift",
    )

    atlas_artifact = json.loads(atlas_artifact_path.read_text(encoding="utf-8"))
    atlas_stored_digest = atlas_artifact.pop("evidence_sha256")
    require(digest_json(atlas_artifact) == atlas_stored_digest, "atlas evidence digest drift")
    require(
        atlas_stored_digest == atlas["independent_run"]["source_evidence_sha256"],
        "atlas linked digest drift",
    )
    require(atlas_artifact["acceptance_passes"] is False, "failed atlas run overclaimed")
    require(
        atlas_artifact["native_UQ_task_progress_eligible"] is False,
        "atlas task progress overclaim",
    )
    require(
        atlas_artifact["acceptance_failures"] == EXPECTED_ATLAS_FAILURES,
        "atlas failure set drift",
    )
    require(
        atlas["independent_run"]["acceptance_failures"] == EXPECTED_ATLAS_FAILURES,
        "linked atlas failure set drift",
    )

    gp = audit["gp_deuterium"]
    require(gp["status"] == "externally_blocked", "GP status drift")
    require(gp["blocked_inputs"] == EXPECTED_BLOCKED_GP_INPUTS, "GP blocker set drift")
    require(gp["exact_abundance_distribution_reproduced"] is False, "GP rerun overclaim")
    gp_artifact = json.loads(gp_artifact_path.read_text(encoding="utf-8"))
    gp_stored_digest = gp_artifact.pop("evidence_sha256")
    require(digest_json(gp_artifact) == gp_stored_digest, "GP evidence digest drift")
    require(gp_stored_digest == gp["source_evidence_sha256"], "GP linked digest drift")
    require(
        gp_artifact["scientific_scope"]["native_UQ_task_progress_eligible"] is False,
        "GP task progress overclaim",
    )
    require(
        sorted(
            key
            for key, unavailable in gp_artifact["reproduction_inputs_unavailable"].items()
            if unavailable
        )
        == sorted(
            [
                "analysis_code",
                "experimental_data_bundle",
                "fitted_hyperparameters",
                "posterior_draws",
                "random_seed",
            ]
        ),
        "GP source blocker set drift",
    )

    return {
        "accepted_baselines": 3,
        "atlas_status": "externally_blocked",
        "audit_valid": True,
        "gp_status": "externally_blocked",
        "native_uq_task_progress_eligible": False,
        "production_authorized": False,
        "task_total": 5,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "audit",
        nargs="?",
        type=Path,
        default=Path("artifacts/benchmarks/NATIVE-UQ-EXTERNAL-BLOCKERS-v1/audit.json"),
    )
    parser.add_argument(
        "--atlas-artifact",
        type=Path,
        default=Path("artifacts/benchmarks/SENSITIVITY-ATLAS-R0-SLICE-v1/artifact.json"),
    )
    parser.add_argument(
        "--gp-artifact",
        type=Path,
        default=Path("artifacts/benchmarks/GP-DEUTERIUM-PRIOR-STRUCTURE-v1/structure.json"),
    )
    args = parser.parse_args()
    print(
        json.dumps(
            validate(args.audit, args.atlas_artifact, args.gp_artifact),
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
