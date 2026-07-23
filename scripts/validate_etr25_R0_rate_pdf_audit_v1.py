#!/usr/bin/env python3
"""Validate the ETR25 R0 descriptive rate-PDF audit and safety boundaries."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import yaml


REACTIONS = {"dp_gamma_he3", "dd_n_he3", "dd_p_t"}
FULL_ROUNDING_COUNTS = {
    "dd_n_he3": (0, 22, 22),
    "dd_p_t": (1, 48, 48),
    "dp_gamma_he3": (9, 18, 22),
}
PRIMARY_ROUNDING_COUNTS = {
    "dd_n_he3": (0, 12, 12),
    "dd_p_t": (0, 25, 25),
    "dp_gamma_he3": (4, 2, 4),
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
    engineering_prior_path: Path,
    repository_root: Path,
) -> dict[str, int]:
    registry = load_yaml(registry_path)
    stage = load_yaml(stage_path)
    engineering = load_yaml(engineering_prior_path)

    if registry.get("schema_version") != 1:
        raise ValueError("unsupported rate-PDF audit schema")
    if registry.get("audit_id") != "ETR25-R0-RATE-PDF-AUDIT-v1":
        raise ValueError("unexpected rate-PDF audit id")
    if registry.get("status") != ("descriptive_rate_pdf_audit_complete_production_prohibited"):
        raise ValueError("rate-PDF audit has an unsafe status")
    if registry.get("production_use") != "prohibited":
        raise ValueError("rate-PDF audit must not authorize production")

    input_record = registry["input"]
    input_path = repository_root / input_record["path"]
    if sha256(input_path) != input_record["sha256"]:
        raise ValueError("ETR25 ingest package SHA256 mismatch")
    output_record = registry["output"]
    output_path = repository_root / output_record["path"]
    if sha256(output_path) != output_record["sha256"]:
        raise ValueError("ETR25 rate-PDF audit SHA256 mismatch")
    audit = json.loads(output_path.read_text(encoding="utf-8"))
    if audit.get("audit_id") != registry["audit_id"]:
        raise ValueError("audit artifact id mismatch")
    if audit["source"]["package_sha256"] != input_record["sha256"]:
        raise ValueError("audit artifact input hash mismatch")

    scopes = audit["temperature_scopes"]
    expected_scopes = {
        "full_table_scope": ([0.001, 10.0], 60),
        "common_solver_evaluated_scope": ([0.06, 10.0], 38),
        "primary_all_R0_unmatched_scope": ([0.06, 2.0], 28),
        "shared_high_temperature_tail": ([2.5, 10.0], 10),
    }
    for name, (bounds, knots) in expected_scopes.items():
        if scopes[name]["T9"] != bounds or scopes[name]["knots"] != knots:
            raise ValueError(f"{name}: temperature scope drift")
    if scopes["primary_all_R0_unmatched_scope"]["not_a_physical_sensitivity_window"] is not True:
        raise ValueError("coverage stratum cannot be called a sensitivity window")
    if scopes["impact_sensitivity_window"]["status"] != "not_yet_measured":
        raise ValueError("unmeasured impact window is overstated")

    if set(audit["reactions"]) != REACTIONS:
        raise ValueError("rate-PDF audit must contain exactly three R0 reactions")
    table_rows = 0
    primary_rows = 0
    max_endpoint_relative_error = 0.0
    max_coherent_error = 0.0
    for reaction_id, reaction in audit["reactions"].items():
        rows = reaction["rows"]
        if len(rows) != 60:
            raise ValueError(f"{reaction_id}: expected 60 audited knots")
        table_rows += len(rows)
        full = reaction["summaries"]["full_table_scope"]
        primary = reaction["summaries"]["primary_all_R0_unmatched_scope"]
        high_tail = reaction["summaries"]["shared_high_temperature_tail"]
        unmatched = reaction["summaries"]["reaction_specific_unmatched_scope"]
        if full["rows"] != 60 or high_tail["rows"] != 10:
            raise ValueError(f"{reaction_id}: audit stratum row-count drift")
        if primary["rows"] != 28 or primary["matched_high_temperature_rows"] != 0:
            raise ValueError(f"{reaction_id}: invalid primary audit stratum")
        primary_rows += primary["rows"]
        expected_full = FULL_ROUNDING_COUNTS[reaction_id]
        observed_full = (
            full["rounding_resolved_lower_endpoint_rows"],
            full["rounding_resolved_upper_endpoint_rows"],
            full["rounding_resolved_any_endpoint_rows"],
        )
        if observed_full != expected_full:
            raise ValueError(f"{reaction_id}: full-scope rounding regression drift")
        expected_primary = PRIMARY_ROUNDING_COUNTS[reaction_id]
        observed_primary = (
            primary["rounding_resolved_lower_endpoint_rows"],
            primary["rounding_resolved_upper_endpoint_rows"],
            primary["rounding_resolved_any_endpoint_rows"],
        )
        if observed_primary != expected_primary:
            raise ValueError(f"{reaction_id}: primary rounding regression drift")
        if unmatched["matched_high_temperature_rows"] != 0:
            raise ValueError(f"{reaction_id}: unmatched stratum includes matched rows")

        max_endpoint_relative_error = max(
            max_endpoint_relative_error,
            primary["max_abs_relative_quantile_error"],
        )
        max_coherent_error = max(
            max_coherent_error,
            full["max_scalar_coherent_q_reconstruction_error"],
        )
        for row in rows:
            lower = row["actual_lower_log_width"]
            upper = row["actual_upper_log_width"]
            sigma = row["lognormal_sigma_ln_factor_uncertainty"]
            if min(lower, upper, sigma) <= 0:
                raise ValueError(f"{reaction_id}: non-positive log width")
            expected_asymmetry = upper - lower
            if not math.isclose(
                row["actual_log_width_asymmetry_upper_minus_lower"],
                expected_asymmetry,
                rel_tol=0,
                abs_tol=1e-15,
            ):
                raise ValueError(f"{reaction_id}: log-asymmetry identity failed")
            expected_scale = 0.5 * (lower + upper) - sigma
            if not math.isclose(
                row["lognormal_scale_mismatch_actual_average_width_minus_sigma"],
                expected_scale,
                rel_tol=0,
                abs_tol=1e-15,
            ):
                raise ValueError(f"{reaction_id}: scale-mismatch identity failed")

    if max_endpoint_relative_error >= 0.002:
        raise ValueError("descriptive primary endpoint error regression drift")
    if max_coherent_error >= 1e-12:
        raise ValueError("scalar coherent identity reconstruction failed")

    scalar = audit["scalar_coherent_validation"]
    if scalar["actual_posterior_curve_claim"] is not False:
        raise ValueError("scalar proxy cannot claim actual posterior curves")
    if scalar["actual_posterior_coherence"] != ("not_evaluable_from_public_pointwise_quantiles"):
        raise ValueError("actual posterior coherence is overstated")
    if scalar["independent_temperature_noise_prohibited"] is not True:
        raise ValueError("independent temperature noise must be prohibited")

    decision = audit["decision"]
    if decision["scalar_lognormal_status"] != ("accepted_as_explicit_coherent_comparator_only"):
        raise ValueError("scalar proxy exceeds comparator scope")
    for key in (
        "equivalence_claim_allowed",
        "cross_reaction_independence_claim_allowed",
        "scientific_label_generation_allowed",
    ):
        if decision[key] is not False:
            raise ValueError(f"unsafe decision flag: {key}")
    if not decision["production_use"].startswith("prohibited_"):
        raise ValueError("audit decision must prohibit production")

    if stage.get("status") != ("public_table_and_rate_pdf_audit_complete_coherent_prior_pending"):
        raise ValueError("Stage-R0 must retain coherent-prior work")
    if stage["rate_pdf_audit"]["registry"] != str(registry_path.relative_to(repository_root)):
        raise ValueError("Stage-R0 does not bind the audit registry")
    if stage["rate_pdf_audit"]["artifact"] != output_record["path"]:
        raise ValueError("Stage-R0 does not bind the audit artifact")
    if any(item["production_enabled"] is not False for item in stage["reactions"]):
        raise ValueError("Stage-R0 production must remain disabled")

    gates = engineering["upstream_scientific_gates"]
    if gates["UQ0_RATE_PDF_AUDIT"] != "complete_descriptive_comparator_only":
        raise ValueError("engineering prior does not record the descriptive audit")
    if gates["coherent_ETR25_or_approved_posterior_prior"] != "pending":
        raise ValueError("coherent scientific prior must remain pending")
    if gates["common_production_adapter_unlocked"] is not False:
        raise ValueError("descriptive audit cannot unlock the production adapter")
    if set(engineering["signoffs"].values()) != {"pending"}:
        raise ValueError("rate-PDF audit cannot manufacture scientific sign-offs")

    return {
        "reactions": len(REACTIONS),
        "table_rows": table_rows,
        "primary_rows": primary_rows,
        "full_rounding_resolved_any_rows": sum(
            values[2] for values in FULL_ROUNDING_COUNTS.values()
        ),
        "primary_rounding_resolved_any_rows": sum(
            values[2] for values in PRIMARY_ROUNDING_COUNTS.values()
        ),
        "production_enabled_reactions": sum(
            bool(item["production_enabled"]) for item in stage["reactions"]
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument("--engineering-prior", type=Path, required=True)
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    summary = validate(
        args.registry.resolve(),
        args.stage.resolve(),
        args.engineering_prior.resolve(),
        args.repository_root.resolve(),
    )
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
