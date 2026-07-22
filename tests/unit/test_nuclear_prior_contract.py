from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "configs/physics/nuclear_prior_NUC-v1.yaml"
DOCUMENT = ROOT / "docs/preregistration/NUCLEAR_PRIOR_FREEZE_v1.md"


def load_registry() -> dict:
    return yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))


def test_nuclear_prior_contract_cannot_be_used_for_production() -> None:
    data = load_registry()

    assert data["decision_status"] == "not_frozen"
    assert data["production_use"] == "prohibited"
    assert data["track_b_gate_status"] == "closed"
    assert data["production_guard"]["allow_training_labels"] is False
    assert data["production_guard"]["allow_track_b_inference"] is False
    assert data["production_guard"]["allow_fisher_gate_inputs"] is False


def test_three_functional_candidate_placeholders_are_explicitly_incomplete() -> None:
    data = load_registry()
    reactions = data["reactions"]

    assert {reaction["reaction_id"] for reaction in reactions} == {
        "dp_gamma_he3",
        "dd_n_he3",
        "dd_p_t",
    }
    assert all(reaction["inclusion_sets"]["functional_candidate"] for reaction in reactions)
    assert all(reaction["production_enabled"] is False for reaction in reactions)
    assert all(
        reaction["functional_prior"]["status"] == "not_constructed" for reaction in reactions
    )
    assert all(reaction["scalar_prior"]["status"] == "pending" for reaction in reactions)


def test_every_reaction_satisfies_the_contract_shape_without_false_completion() -> None:
    data = load_registry()
    required = set(data["reaction_entry_required_fields"])

    for reaction in data["reactions"]:
        assert required <= reaction.keys()
        assert reaction["nuclear_data"]["source_id"] == "pending"
        assert reaction["provenance"]["source_checksums"] == "pending"
        assert reaction["correlations"]["independence_assumed"] is False
        assert reaction["solver_mappings"]["status"] == "not_validated"


def test_missing_correlations_do_not_become_independence_assumptions() -> None:
    data = load_registry()

    assert data["correlation_policy"]["independence_assumed"] is False
    assert data["correlation_policy"]["status"] == "not_evaluated"
    assert "does not imply independence" in data["correlation_policy"]["missing_correlation_rule"]


def test_neutron_lifetime_is_an_external_nonduplicated_prior() -> None:
    neutron = load_registry()["neutron_lifetime"]

    assert neutron["modeled_separately"] is True
    assert neutron["registry_reference"] == "configs/physics/neutron_lifetime_v1.yaml"
    assert neutron["double_counting_prohibited"] is True


def test_document_keeps_track_b_closed_and_signoffs_pending() -> None:
    text = DOCUMENT.read_text(encoding="utf-8")

    assert "NOT FROZEN; PRODUCTION USE PROHIBITED" in text
    assert "A03 nuclear-data review: **pending**" in text
    assert "A00 scientific lead: **pending**" in text
    assert "A09 independent validation: **pending**" in text
    assert "Track B remains **NOT FROZEN**" in text
