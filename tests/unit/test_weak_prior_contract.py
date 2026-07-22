from __future__ import annotations

import importlib.util
import math
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "configs/physics/weak_prior_WEAK-v1.yaml"
NEUTRON = ROOT / "configs/physics/neutron_lifetime_v1.yaml"
SCRIPT = ROOT / "scripts/validate_weak_prior_contract.py"
DOCUMENT = ROOT / "docs/preregistration/WEAK_PRIOR_CONTRACT_v1.md"


def load_module():
    spec = importlib.util.spec_from_file_location("weak_prior_validator", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_contract_validates_but_does_not_claim_scientific_readiness() -> None:
    module = load_module()
    report = module.validate_contract(load_yaml(CONTRACT), load_yaml(NEUTRON))

    assert report["solver_count"] == 3
    assert report["scientific_readiness"] == "not_ready"
    assert report["production_use"] == "prohibited_pending_signoff_and_numerical_regression"
    assert report["status"] == "valid_implementation_contract_not_scientifically_signed"


def test_canonical_N0_mapping_is_exact_for_all_three_solvers() -> None:
    module = load_module()
    contract = load_yaml(CONTRACT)

    assert math.isclose(
        module.canonical_tau_to_native(contract, "LINX", 878.3),
        878.3 / 879.4,
        rel_tol=0,
        abs_tol=1e-15,
    )
    assert module.canonical_tau_to_native(contract, "PRyMordial", 878.3) == 878.3
    assert module.canonical_tau_to_native(contract, "PRIMAT", 878.3) == 878.3


@pytest.mark.parametrize("value", [0.0, -1.0, math.inf, math.nan])
def test_canonical_mapping_rejects_nonphysical_lifetimes(value: float) -> None:
    module = load_module()
    with pytest.raises(ValueError, match="finite and positive"):
        module.canonical_tau_to_native(load_yaml(CONTRACT), "LINX", value)


def test_weak_theory_normalization_is_registered_but_inactive() -> None:
    contract = load_yaml(CONTRACT)
    weak_norm = contract["canonical_variables"]["weak_theory_normalization"]
    sampling = contract["sampling_contract"]

    assert weak_norm["canonical_name"] == "w_weak_norm"
    assert weak_norm["status"] == "fixed_not_sampled_no_reviewed_prior_registered"
    assert sampling["active_R0_continuous_weak_nuisances"] == ["tau_n_seconds"]
    assert sampling["inactive_R0_weak_nuisances"] == ["w_weak_norm"]
    assert sampling["solver_native_tau_n_sampling"] == "disabled"


def test_solver_specific_double_counting_controls_are_explicit() -> None:
    mappings = load_yaml(CONTRACT)["solver_mappings"]

    assert "Do not pre-scale" in " ".join(mappings["LINX"]["adapter_rules"])
    assert mappings["PRyMordial"]["required_fixed_controls"]["tau_n_flag"] is True
    assert mappings["PRyMordial"]["required_fixed_controls"]["NP_nTOp_flag"] is False
    assert mappings["PRIMAT"]["required_fixed_controls"]["std_tau_n"] == 0.0
    assert mappings["PRIMAT"]["required_fixed_controls"]["native_mc"] is False


def test_every_source_mapping_is_hash_bound_but_numerical_regression_is_pending() -> None:
    mappings = load_yaml(CONTRACT)["solver_mappings"]

    for mapping in mappings.values():
        assert len(mapping["revision"]) == 40
        assert mapping["source_audit_status"] == "complete"
        assert mapping["numerical_regression_status"] == "pending_UQ0_NUISANCE_ADAPTER"
        assert len(mapping["source_evidence"]) >= 2
        for evidence in mapping["source_evidence"]:
            assert len(evidence["git_blob"]) == 40
            assert len(evidence["sha256"]) == 64


def test_document_keeps_signoffs_and_production_gate_pending() -> None:
    text = DOCUMENT.read_text(encoding="utf-8")

    assert "scientific sign-off pending; production use prohibited" in text
    assert "not authorize production labels" in text
    assert "A00 scientific approval" in text
    assert "independent weak-physics review" in text
    assert "ready_for_production_labels: false" in text
