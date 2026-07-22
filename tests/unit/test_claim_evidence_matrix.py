from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "configs/claims/claim_evidence_matrix_v1.yaml"
DOCUMENT = ROOT / "docs/claims/CLAIM_EVIDENCE_MATRIX_v1.md"


def load_registry() -> dict:
    return yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))


def test_claim_ids_tiers_and_falsifiers_are_explicit() -> None:
    data = load_registry()
    claims = data["claims"]

    assert len(claims) == 9
    assert len({claim["claim_id"] for claim in claims}) == len(claims)
    assert {claim["tier"] for claim in claims} == {"C0", "C1", "C2", "C3", "C4"}
    for claim in claims:
        assert claim["task_ids"]
        assert claim["candidate_statement"]
        assert claim["falsifier"]
        assert claim["required_signoffs"]
        assert claim["signoff_status"] == "pending"


def test_no_c2_c3_or_c4_claim_is_cleared_without_evidence() -> None:
    claims = load_registry()["claims"]

    for claim in claims:
        if claim["tier"] in {"C2", "C3", "C4"}:
            assert claim["current_status"] == "unavailable"
            assert claim["allowed_scope"] == []
            assert claim["evidence"] == []
            assert claim["missing_evidence"]


def test_existing_c0_c1_evidence_is_scope_limited() -> None:
    claims = {claim["claim_id"]: claim for claim in load_registry()["claims"]}

    linx = claims["C1-LINX-STANDARD-NUMERICS-01"]
    assert linx["current_status"] == "scope_limited_evidence"
    assert linx["allowed_scope"] == [
        "one_standard_fiducial_point",
        "rtol_1e_minus_8_atol_1e_minus_11_sampling_2400_max_steps_16384",
    ]
    assert linx["prohibited_generalization"] == "not_a_global_LINX_fidelity_or_gradient_claim"

    cost = claims["C1-DIRECT-SOLVER-COST-01"]
    assert cost["current_status"] == "incomplete"
    assert "W1_final_validated_artifact" in cost["missing_evidence"]
    assert "W3_component_and_full_joint_stack_measurements" in cost["missing_evidence"]


def test_document_keeps_claim_and_nature_gates_closed() -> None:
    text = DOCUMENT.read_text(encoding="utf-8")

    assert "claims not frozen" in text
    assert "A00 scientific lead: **pending**" in text
    assert "A09 independent validation: **pending**" in text
    assert "A11 literature and competition: **pending**" in text
    assert "Track B remains **NOT FROZEN**" in text
    assert "Nature-tier gate remains **CLOSED**" in text
