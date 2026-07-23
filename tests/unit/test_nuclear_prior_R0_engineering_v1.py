from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from scripts.validate_nuclear_prior_R0_engineering_v1 import validate


ROOT = Path(__file__).resolve().parents[2]
PRIOR = ROOT / "configs/physics/nuclear_prior_R0_engineering_v1.yaml"
STAGE = ROOT / "configs/physics/nuclear_stage0_R0_v1.yaml"


def test_legacy_mapping_validates_and_keeps_production_closed() -> None:
    summary = validate(PRIOR, STAGE, ROOT)

    assert summary == {
        "canonical_parameters": 3,
        "mapped_solver_paths": 3,
        "registered_reactions": 3,
        "pending_signoffs": 3,
        "production_enabled_reactions": 0,
    }


def test_each_solver_maps_exactly_three_canonical_parameters() -> None:
    prior = yaml.safe_load(PRIOR.read_text(encoding="utf-8"))
    expected = {"z_dp_gamma_he3", "z_dd_n_he3", "z_dd_p_t"}

    for mapping in prior["solver_mappings"].values():
        assert set(mapping["reaction_parameters"]) == expected
        assert mapping["native_sampling"] == "prohibited_use_external_manifest"


def test_unmatched_native_libraries_cannot_be_called_engine_discrepancy() -> None:
    prior = yaml.safe_load(PRIOR.read_text(encoding="utf-8"))
    interpretation = prior["factorial_interpretation"]

    assert interpretation["common_z_interface_across_three_solvers"] is True
    assert interpretation["matched_rate_library_across_three_solvers"] is False
    assert interpretation["engine_discrepancy_claim_allowed"] is False


def test_legacy_mapping_does_not_unlock_ETR25_production_adapter() -> None:
    prior = yaml.safe_load(PRIOR.read_text(encoding="utf-8"))

    assert (
        prior["upstream_scientific_gates"]["UQ0_ETR25_R0_INGEST"] == "complete_public_products_only"
    )
    assert prior["upstream_scientific_gates"]["UQ0_RATE_PDF_AUDIT"] == "pending"
    assert prior["upstream_scientific_gates"]["common_production_adapter_unlocked"] is False


def test_validator_rejects_manufactured_signoff(tmp_path: Path) -> None:
    prior = yaml.safe_load(PRIOR.read_text(encoding="utf-8"))
    prior["signoffs"]["A03_nuclear_data_review"] = "approved"
    modified = tmp_path / "prior.yaml"
    modified.write_text(yaml.safe_dump(prior, sort_keys=False), encoding="utf-8")

    with pytest.raises(ValueError, match="cannot manufacture"):
        validate(modified, STAGE, ROOT)
