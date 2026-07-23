from pathlib import Path

from scripts.validate_R0_reference_prior_v1 import validate


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_reference_prior_contract_is_self_contained_and_fail_closed() -> None:
    summary = validate(
        REPOSITORY_ROOT / "configs/physics/nuclear_prior_R0_reference_v1.yaml",
        REPOSITORY_ROOT,
    )

    assert summary == {
        "prior_id": "NUCLEAR-R0-REFERENCE-v1",
        "reactions": 3,
        "representations": 3,
        "correlation_models": 35,
        "GH81_nodes": 81,
        "omega_b_h2_points": 5,
        "exploratory_direct_calculation_allowed": True,
    }
