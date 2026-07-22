from __future__ import annotations

import importlib.util
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/validate_nuclear_stage0_R0_source_candidates.py"
CANDIDATES = ROOT / "configs/physics/nuclear_stage0_R0_source_candidates_v1.yaml"
CAPTURE = (
    ROOT
    / "artifacts/provenance/PUBLIC-NUCLEAR-RATE-PROVENANCE-v1"
    / "capture-20260722T200435Z.json"
)
STAGE = ROOT / "configs/physics/nuclear_stage0_R0_v1.yaml"


def load_module():
    spec = importlib.util.spec_from_file_location("r0_source_candidates", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_candidate_audit_is_exactly_bound_and_does_not_freeze_a_prior() -> None:
    module = load_module()

    summary = module.validate(CANDIDATES, CAPTURE, STAGE)

    assert summary == {
        "candidate_collections": 7,
        "bound_files": 21,
        "unique_byte_payloads": 18,
        "copied_lineage_hashes": 3,
        "pending_selection_gates": 12,
    }


def test_all_candidates_are_nonproduction_filename_mappings() -> None:
    data = yaml.safe_load(CANDIDATES.read_text(encoding="utf-8"))

    assert data["production_use"] == "prohibited"
    assert data["numerical_prior_credit"] is False
    assert data["selection"]["primary_candidate_id"] is None
    assert all(
        candidate["mapping_status"] == "filename_token_candidate_only"
        for candidate in data["candidate_collections"]
    )
    assert all(
        candidate["numerical_prior_credit"] is False for candidate in data["candidate_collections"]
    )


def test_copied_linx_bytes_are_not_independent_nuclear_evidence() -> None:
    data = yaml.safe_load(CANDIDATES.read_text(encoding="utf-8"))
    groups = data["copied_lineage_groups"]

    assert len(groups) == 1
    assert set(groups[0]["candidate_ids"]) == {
        "linx_key_primat_2023",
        "abcmb_bundled_linx_key_primat_2023",
    }
    assert groups[0]["independent_nuclear_evidence"] is False


def test_every_scientific_selection_gate_remains_pending() -> None:
    data = yaml.safe_load(CANDIDATES.read_text(encoding="utf-8"))

    checklist = data["source_selection_checklist"]
    assert checklist
    assert {item["status"] for item in checklist} == {"pending"}
