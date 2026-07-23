from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import yaml

from scripts.validate_etr25_R0_rate_pdf_audit_v1 import validate


ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "configs/physics/etr25_R0_rate_pdf_audit_v1.yaml"
STAGE = ROOT / "configs/physics/nuclear_stage0_R0_v1.yaml"
ENGINEERING = ROOT / "configs/physics/nuclear_prior_R0_engineering_v1.yaml"
AUDIT = ROOT / "artifacts/priors/ETR25-R0-RATE-PDF-AUDIT-v1/audit.json"


def test_rate_pdf_audit_validates_without_unlocking_production() -> None:
    assert validate(REGISTRY, STAGE, ENGINEERING, ROOT) == {
        "reactions": 3,
        "table_rows": 180,
        "primary_rows": 84,
        "full_rounding_resolved_any_rows": 92,
        "primary_rounding_resolved_any_rows": 41,
        "production_enabled_reactions": 0,
    }


def test_audit_is_pinned_to_registry_hash() -> None:
    registry = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    assert hashlib.sha256(AUDIT.read_bytes()).hexdigest() == registry["output"]["sha256"]


def test_primary_scope_is_coverage_not_sensitivity() -> None:
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    primary = audit["temperature_scopes"]["primary_all_R0_unmatched_scope"]

    assert primary["T9"] == [0.06, 2.0]
    assert primary["knots"] == 28
    assert primary["not_a_physical_sensitivity_window"] is True
    assert audit["temperature_scopes"]["impact_sensitivity_window"]["status"] == "not_yet_measured"


def test_actual_posterior_coherence_is_not_claimed() -> None:
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    scalar = audit["scalar_coherent_validation"]

    assert scalar["actual_posterior_curve_claim"] is False
    assert scalar["actual_posterior_coherence"] == "not_evaluable_from_public_pointwise_quantiles"
    assert scalar["independent_temperature_noise_prohibited"] is True


def test_validator_rejects_production_unlock(tmp_path: Path) -> None:
    engineering = yaml.safe_load(ENGINEERING.read_text(encoding="utf-8"))
    engineering["upstream_scientific_gates"]["common_production_adapter_unlocked"] = True
    bad_engineering = tmp_path / "engineering.yaml"
    bad_engineering.write_text(
        yaml.safe_dump(engineering, sort_keys=False),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="cannot unlock"):
        validate(REGISTRY, STAGE, bad_engineering, ROOT)
