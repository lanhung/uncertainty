from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import yaml

from scripts.validate_R0_prior_candidate_v1 import validate


ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "configs/physics/nuclear_prior_R0_candidate_v1.yaml"
STAGE = ROOT / "configs/physics/nuclear_stage0_R0_v1.yaml"
ENGINEERING = ROOT / "configs/physics/nuclear_prior_R0_engineering_v1.yaml"
COMPARATORS = ROOT / "artifacts/priors/ETR25-R0-COHERENT-COMPARATORS-v1/package.json"
CONTRACT = ROOT / "artifacts/priors/R0-PRIOR-CANDIDATE-CONTRACT-v1/package.json"


def test_R0_candidate_validates_without_scientific_acceptance() -> None:
    assert validate(REGISTRY, STAGE, ENGINEERING, ROOT) == {
        "reactions": 3,
        "comparator_rows": 180,
        "correlation_models": 35,
        "unique_correlation_matrices": 34,
        "accepted_scientific_prior_reactions": 0,
        "production_enabled_reactions": 0,
    }


def test_candidate_artifacts_are_hash_pinned() -> None:
    registry = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))

    assert (
        hashlib.sha256(COMPARATORS.read_bytes()).hexdigest()
        == registry["candidate_artifacts"]["coherent_comparators"]["sha256"]
    )
    assert (
        hashlib.sha256(CONTRACT.read_bytes()).hexdigest()
        == registry["candidate_artifacts"]["candidate_contract"]["sha256"]
    )


def test_quantile_surrogate_is_not_actual_posterior() -> None:
    comparators = json.loads(COMPARATORS.read_text(encoding="utf-8"))
    surrogate = comparators["quantile_matched_asymmetric_rank1_surrogate"]

    assert surrogate["actual_posterior_reconstruction"] is False
    assert surrogate["validated_nuclear_input_coherence"] is False
    assert surrogate["role"] == "explicit_asymmetric_comparator_and_stress_model_only"
    assert comparators["safety"]["scientific_prior_selected"] is False
    assert comparators["safety"]["production_use"] == "prohibited"


def test_PRIMAT_reverse_cap_caveat_is_machine_enforced() -> None:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    primat = contract["solver_reverse_status"]["PRIMAT"]

    assert primat["strict_same_draw_detailed_balance_unconditional"] is False
    assert primat["consecutive_draw_cache_regression_required"] is True
    assert (
        primat["native_reverse_cap"]
        == "load_time_median_QED_forward_not_recomputed_by_apply_variations"
    )


def test_validator_rejects_hidden_PRIMAT_cap(tmp_path: Path) -> None:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    contract["solver_reverse_status"]["PRIMAT"][
        "strict_same_draw_detailed_balance_unconditional"
    ] = True
    bad_contract = tmp_path / "contract.json"
    bad_contract.write_text(json.dumps(contract), encoding="utf-8")

    registry = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    record = registry["candidate_artifacts"]["candidate_contract"]
    record["path"] = str(bad_contract)
    record["sha256"] = hashlib.sha256(bad_contract.read_bytes()).hexdigest()
    bad_registry = tmp_path / "registry.yaml"
    bad_registry.write_text(
        yaml.safe_dump(registry, sort_keys=False),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="reverse cap"):
        validate(bad_registry, STAGE, ENGINEERING, ROOT)
