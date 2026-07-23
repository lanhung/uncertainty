#!/usr/bin/env python3
"""Validate the ETR25 R0 public-product ingest and its evidence boundaries."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import yaml


REACTIONS = {"dp_gamma_he3", "dd_n_he3", "dd_p_t"}
EXPECTED_TABLES = {
    "dp_gamma_he3": (6, 5.0),
    "dd_n_he3": (7, 2.5),
    "dd_p_t": (8, 2.5),
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected a mapping in {path}")
    return payload


def validate(
    registry_path: Path,
    stage_path: Path,
    repository_root: Path,
) -> dict[str, int]:
    registry = load_yaml(registry_path)
    stage = load_yaml(stage_path)

    if registry.get("schema_version") != 1:
        raise ValueError("unsupported ETR25 ingest schema")
    if registry.get("registry_id") != "ETR25-R0-INGEST-v1":
        raise ValueError("unexpected ETR25 ingest registry id")
    if registry.get("status") != "R0_percentile_tables_captured_rate_pdf_audit_complete":
        raise ValueError("ETR25 ingest must record the completed descriptive audit")
    if registry.get("production_use") != "prohibited":
        raise ValueError("ETR25 public-table ingest must not authorize production")

    package_record = registry["derived_package"]
    package_path = repository_root / package_record["path"]
    if sha256(package_path) != package_record["sha256"]:
        raise ValueError("ETR25 package SHA256 mismatch")
    package = json.loads(package_path.read_text(encoding="utf-8"))
    if package.get("package_id") != "ETR25-R0-TABLES-v1":
        raise ValueError("unexpected ETR25 package id")
    if not str(package.get("production_use", "")).startswith("prohibited_"):
        raise ValueError("ETR25 package must prohibit production use")
    if package["machine_readable_source"]["role"] != ("primary_exact_table_byte_source"):
        raise ValueError("official IOP ASCII must be the primary byte source")
    if package["machine_readable_source"]["pinning_contract"] != ("full_url_plus_size_plus_sha256"):
        raise ValueError("publisher products must be pinned by URL, size and SHA256")

    source_boundary = package["source_boundary"]
    required_false = {
        "full_actual_density_or_posterior_samples_available",
        "coherent_actual_temperature_draws_reconstructible",
        "missing_covariance_is_independence_evidence",
    }
    if any(source_boundary.get(key) is not False for key in required_false):
        raise ValueError("package crosses the published-posterior evidence boundary")
    if source_boundary.get("scalar_lognormal_coherent_approximation_available") is not True:
        raise ValueError("registered scalar coherent approximation is missing")
    if source_boundary["cross_temperature_covariance"] != ("not_published_in_identified_release"):
        raise ValueError("cross-temperature covariance status is overstated")
    if source_boundary["cross_reaction_covariance"] != ("not_published_in_identified_release"):
        raise ValueError("cross-reaction covariance status is overstated")

    if set(package["reactions"]) != REACTIONS:
        raise ValueError("package must contain exactly the three R0 reactions")
    registry_tables = registry["official_machine_readable_tables"]["tables"]
    if set(registry_tables) != REACTIONS:
        raise ValueError("registry table set differs from R0")
    registry_reactions = registry["reactions"]
    if set(registry_reactions) != REACTIONS:
        raise ValueError("registry reaction set differs from R0")

    common_grid: list[float] | None = None
    matched_rows = 0
    for reaction_id, (table_number, match_start) in EXPECTED_TABLES.items():
        reaction = package["reactions"][reaction_id]
        table_record = registry_tables[reaction_id]
        reaction_record = registry_reactions[reaction_id]
        if reaction["table_number"] != table_number:
            raise ValueError(f"{reaction_id}: wrong table number")
        if reaction["ascii_sha256"] != table_record["sha256"]:
            raise ValueError(f"{reaction_id}: ASCII SHA256 registry mismatch")
        if reaction["ascii_size_bytes"] != table_record["size_bytes"]:
            raise ValueError(f"{reaction_id}: ASCII size registry mismatch")
        if reaction["ascii_url"] != table_record["URL"]:
            raise ValueError(f"{reaction_id}: ASCII URL registry mismatch")
        if reaction["ascii_sha256"] != reaction_record["source_ascii_sha256"]:
            raise ValueError(f"{reaction_id}: source SHA256 mismatch")
        if reaction["rows_sha256"] != reaction_record["rows_sha256"]:
            raise ValueError(f"{reaction_id}: row payload SHA256 mismatch")
        if reaction["arxiv_tex_crosscheck"] != ("exact_numeric_and_parenthesis_match"):
            raise ValueError(f"{reaction_id}: independent source cross-check missing")

        rows = reaction["rows"]
        if len(rows) != 60:
            raise ValueError(f"{reaction_id}: expected 60 table knots")
        grid = [row["T9"] for row in rows]
        if common_grid is None:
            common_grid = grid
        elif grid != common_grid:
            raise ValueError("R0 reactions must share one temperature grid")
        for row in rows:
            if not row["low_p16"] <= row["median_p50"] <= row["high_p84"]:
                raise ValueError(f"{reaction_id}: invalid percentile ordering")
            if row["factor_uncertainty_lognormal"] < 1:
                raise ValueError(f"{reaction_id}: factor uncertainty below one")
        matched = [row for row in rows if row["high_temperature_matched_rate"]]
        if not matched or min(row["T9"] for row in matched) != match_start:
            raise ValueError(f"{reaction_id}: wrong high-temperature match boundary")
        matched_rows += len(matched)

        percentile = reaction["percentile_semantics"]
        factor = reaction["factor_uncertainty_semantics"]
        if percentile["source"] != "actual_rate_probability_density":
            raise ValueError(f"{reaction_id}: actual-percentile semantics lost")
        if factor["model"] != "lognormal_approximation":
            raise ValueError(f"{reaction_id}: factor uncertainty semantics lost")
        if factor["not_derived_directly_from_actual_percentiles"] is not True:
            raise ValueError(f"{reaction_id}: actual and lognormal products conflated")

    assert common_grid is not None
    if len(common_grid) != 60 or min(common_grid) != 0.001 or max(common_grid) != 10.0:
        raise ValueError("unexpected ETR25 common T9 grid")

    availability = registry["availability_boundary"]
    if availability["coherent_random_curve_draws"] != (
        "not_reconstructible_from_percentiles_alone"
    ):
        raise ValueError("registry overstates coherent actual-posterior availability")
    if availability["missing_covariance_is_evidence_of_independence"] is not False:
        raise ValueError("missing covariance cannot authorize independence")
    prohibited = set(registry["next_gate"]["prohibited_without_additional_model"])
    if {
        "claim_full_actual_PDF_reconstruction",
        "sample_independent_temperature_bins",
        "claim_cross_reaction_independence",
        "generate_scientific_BBN_labels",
    } - prohibited:
        raise ValueError("next-gate prohibition list is incomplete")

    stage_reactions = {item["reaction_id"]: item for item in stage["reactions"]}
    if set(stage_reactions) != REACTIONS:
        raise ValueError("Stage-R0 registry reaction set differs from the ingest")
    if stage.get("status") != ("public_table_and_rate_pdf_audit_complete_coherent_prior_pending"):
        raise ValueError("Stage-R0 status must retain the coherent-prior gate")
    if stage["nuisance_contract"]["actual_pdf_model"]["status"] != (
        "pointwise_percentiles_ingested_coherent_actual_posterior_unavailable"
    ):
        raise ValueError("Stage-R0 must not claim an actual posterior model")
    if any(item.get("production_enabled") is not False for item in stage_reactions.values()):
        raise ValueError("Stage-R0 production must remain disabled")

    return {
        "reactions": len(REACTIONS),
        "temperature_knots_per_reaction": len(common_grid),
        "table_rows": len(REACTIONS) * len(common_grid),
        "high_temperature_matched_rows": matched_rows,
        "production_enabled_reactions": sum(
            bool(item["production_enabled"]) for item in stage_reactions.values()
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    summary = validate(
        args.registry.resolve(),
        args.stage.resolve(),
        args.repository_root.resolve(),
    )
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
