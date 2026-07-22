#!/usr/bin/env python3
"""Validate the R0 source-candidate audit against the captured public bytes."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import yaml


REACTIONS = {"dp_gamma_he3", "dd_n_he3", "dd_p_t"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected a mapping in {path}")
    return payload


def captured_files(capture: dict[str, Any]) -> set[tuple[str, str, str, str]]:
    rows: set[tuple[str, str, str, str]] = set()
    for repository_name, repository in capture["repositories"].items():
        for collection_name, files in repository["collections"].items():
            for item in files:
                rows.add(
                    (
                        repository_name,
                        collection_name,
                        item["path"],
                        item["sha256"],
                    )
                )
    return rows


def validate(candidate_path: Path, capture_path: Path, stage_path: Path) -> dict[str, int]:
    candidates = load_yaml(candidate_path)
    stage = load_yaml(stage_path)
    capture = json.loads(capture_path.read_text(encoding="utf-8"))

    if candidates.get("schema_version") != 1:
        raise ValueError("unsupported candidate-audit schema")
    if candidates.get("audit_id") != "NUCLEAR-STAGE0-R0-SOURCE-CANDIDATES-v1":
        raise ValueError("unexpected candidate-audit id")
    if candidates.get("status") != "provenance_bound_scientific_selection_pending":
        raise ValueError("candidate audit must keep scientific selection pending")
    if candidates.get("production_use") != "prohibited":
        raise ValueError("candidate audit must prohibit production use")
    if candidates.get("numerical_prior_credit") is not False:
        raise ValueError("candidate audit must not award numerical-prior credit")
    if candidates["selection"].get("primary_candidate_id") is not None:
        raise ValueError("no primary rate source may be selected by this audit")
    if candidates["selection"].get("primary_selection_status") != "pending_A03_review":
        raise ValueError("primary source selection must remain pending A03 review")

    expected_capture_digest = candidates["scope"]["captured_inventory_sha256"]
    if sha256(capture_path) != expected_capture_digest:
        raise ValueError("captured public inventory SHA256 does not match the audit")
    if capture.get("status") != "captured_inventory_only_not_nuc_freeze":
        raise ValueError("input capture has an unsafe scientific status")

    stage_reactions = {item["reaction_id"] for item in stage.get("reactions", [])}
    if stage_reactions != REACTIONS:
        raise ValueError("Stage-0 contract does not contain exactly the three R0 reactions")
    if any(item.get("production_enabled") is not False for item in stage["reactions"]):
        raise ValueError("a Stage-0 reaction is unexpectedly production enabled")
    if set(candidates["scope"]["reactions"]) != REACTIONS:
        raise ValueError("candidate audit reaction scope differs from Stage-0")

    inventory_rows = captured_files(capture)
    candidate_rows: set[tuple[str, str, str, str]] = set()
    candidate_ids: set[str] = set()
    for candidate in candidates.get("candidate_collections", []):
        candidate_id = candidate["candidate_id"]
        if candidate_id in candidate_ids:
            raise ValueError(f"duplicate candidate id: {candidate_id}")
        candidate_ids.add(candidate_id)
        if candidate.get("mapping_status") != "filename_token_candidate_only":
            raise ValueError(f"{candidate_id} overstates mapping validation")
        if candidate.get("numerical_prior_credit") is not False:
            raise ValueError(f"{candidate_id} awards numerical-prior credit")
        if set(candidate.get("reactions", {})) != REACTIONS:
            raise ValueError(f"{candidate_id} does not map all three R0 reactions")

        captured_repository = capture["repositories"].get(candidate["repository"])
        if not captured_repository:
            raise ValueError(f"{candidate_id} references an uncaptured repository")
        if candidate["revision"] != captured_repository["revision"]:
            raise ValueError(f"{candidate_id} revision differs from the capture")
        if candidate["license"] != captured_repository["license"]:
            raise ValueError(f"{candidate_id} license differs from the capture")
        if candidate["collection"] not in captured_repository["collections"]:
            raise ValueError(f"{candidate_id} references an uncaptured collection")

        for item in candidate["reactions"].values():
            candidate_rows.add(
                (
                    candidate["repository"],
                    candidate["collection"],
                    item["path"],
                    item["sha256"],
                )
            )

    if candidate_rows != inventory_rows:
        missing = sorted(inventory_rows - candidate_rows)
        extra = sorted(candidate_rows - inventory_rows)
        raise ValueError(f"candidate rows differ from capture; missing={missing}, extra={extra}")

    captured_duplicate_hashes = {
        group["sha256"] for group in capture.get("duplicate_content_groups", [])
    }
    declared_duplicate_hashes: set[str] = set()
    for group in candidates.get("copied_lineage_groups", []):
        if group.get("independent_nuclear_evidence") is not False:
            raise ValueError("copied bytes cannot count as independent nuclear evidence")
        if not set(group["candidate_ids"]) <= candidate_ids:
            raise ValueError("copied-lineage group references an unknown candidate")
        declared_duplicate_hashes.update(group["sha256_values"])
    if declared_duplicate_hashes != captured_duplicate_hashes:
        raise ValueError("copied-lineage hashes do not match captured duplicate groups")

    checklist = candidates.get("source_selection_checklist", [])
    checklist_ids = {item["id"] for item in checklist}
    mandatory = {
        "underlying_primary_publication_and_data_release",
        "table_column_and_temperature_semantics",
        "central_curve_units_and_grid",
        "scalar_sigma_T_or_posterior_draw_definition",
        "shared_normalization_and_cross_reaction_covariance",
        "detailed_balance_and_reverse_rate_mapping",
        "solver_internal_rate_id_and_nuisance_transform",
        "plus_minus_one_regression",
        "A03_nuclear_data_review",
        "A00_scientific_signoff",
        "A09_independent_validation",
    }
    if not mandatory <= checklist_ids:
        raise ValueError("source-selection checklist omits mandatory gates")
    if any(item.get("status") != "pending" for item in checklist):
        raise ValueError("this provenance-only audit cannot close scientific selection gates")

    return {
        "candidate_collections": len(candidate_ids),
        "bound_files": len(candidate_rows),
        "unique_byte_payloads": len({row[3] for row in candidate_rows}),
        "copied_lineage_hashes": len(captured_duplicate_hashes),
        "pending_selection_gates": len(checklist),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--capture", type=Path, required=True)
    parser.add_argument("--stage", type=Path, required=True)
    args = parser.parse_args()
    summary = validate(args.candidates, args.capture, args.stage)
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
