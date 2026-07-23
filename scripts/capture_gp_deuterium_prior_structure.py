#!/usr/bin/env python3
"""Capture and fail-close the public 2026 GP deuterium-prior structure."""

from __future__ import annotations

import argparse
import hashlib
import json
import tarfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


REQUIRED_TEX_MARKERS = {
    "conditional_posterior": r"\label{eqn:gp_conditional}",
    "thermal_average": r"\label{eqn:thermal_average}",
    "experimental_offdiagonal": r"\label{eqn:offdiag}",
    "lognormal_mapping": r"\label{eqn:lognormal}",
    "combined_kernel": r"\label{eqn:kernel}",
    "leave_dataset_out": r"\label{eqn:full_ldo}",
    "published_fixed_omega_result": r"\label{eqn:D_H_partial}",
    "code_release_deferred": "Code for our analysis will be released",
}


def digest_json(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def load_tex(archive: Path, expected_path: str) -> bytes:
    with tarfile.open(archive, "r:*") as handle:
        candidates = [
            member
            for member in handle.getmembers()
            if member.isfile() and Path(member.name).name == expected_path
        ]
        if len(candidates) != 1:
            raise ValueError(f"expected exactly one {expected_path} in source archive")
        stream = handle.extractfile(candidates[0])
        if stream is None:
            raise ValueError("could not read TeX source member")
        return stream.read()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-archive", required=True, type=Path)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/benchmarks/gp_deuterium_prior_structure_v1.yaml"),
    )
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    protocol = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    source_bytes = args.source_archive.read_bytes()
    source_hash = sha256_bytes(source_bytes)
    if source_hash != protocol["source"]["source_archive_sha256"]:
        raise ValueError("arXiv source archive hash drift")
    tex_bytes = load_tex(args.source_archive, protocol["source"]["tex_path"])
    tex_hash = sha256_bytes(tex_bytes)
    if tex_hash != protocol["source"]["tex_sha256"]:
        raise ValueError("arXiv TeX source hash drift")
    tex = tex_bytes.decode("utf-8")
    markers = {name: marker in tex for name, marker in REQUIRED_TEX_MARKERS.items()}
    if not all(markers.values()):
        missing = sorted(name for name, present in markers.items() if not present)
        raise ValueError(f"required paper structure markers absent: {missing}")

    unavailable = {
        "analysis_code": not bool(protocol["source"]["analysis_code_public"]),
        "fitted_hyperparameters": not bool(protocol["source"]["fitted_hyperparameters_public"]),
        "posterior_draws": not bool(protocol["source"]["posterior_draws_public"]),
        "experimental_data_bundle": not bool(protocol["source"]["experimental_data_bundle_public"]),
        "random_seed": not bool(protocol["source"]["random_seed_public"]),
    }
    if not all(unavailable.values()):
        raise ValueError("availability state changed; protocol requires a new audit")

    payload: dict[str, Any] = {
        "schema_version": 1,
        "artifact_id": "GP-DEUTERIUM-PRIOR-STRUCTURE-v1",
        "task_id": "UQ0-NATIVE-UQ-REPRO",
        "status": "public_structure_captured_abundance_rerun_blocked",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": {
            **protocol["source"],
            "observed_source_archive_sha256": source_hash,
            "observed_tex_sha256": tex_hash,
        },
        "required_tex_markers": markers,
        "prior_structure": protocol["prior_structure"],
        "published_abundance_references": protocol["published_abundance_references"],
        "reproduction_inputs_unavailable": unavailable,
        "acceptance_boundary": protocol["acceptance_boundary"],
        "scientific_scope": {
            "claim_level": "C0_public_method_structure_audit_only",
            "exact_abundance_distribution_reproduced": False,
            "native_UQ_task_progress_eligible": False,
            "accepted_project_prior": False,
            "production_authorized": False,
            "novelty_claim": False,
        },
        "next_unblock_condition": (
            "A public release of the analysis code, fitted hyperparameters, exact "
            "experimental data bundle and seeded posterior/draw manifest sufficient "
            "to rerun the published abundance distribution."
        ),
    }
    payload["evidence_sha256"] = digest_json(payload)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "output": str(args.output),
                "evidence_sha256": payload["evidence_sha256"],
                "native_UQ_task_progress_eligible": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
