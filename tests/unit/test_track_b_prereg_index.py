from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "configs/preregistration/track_b_prereg_v1.yaml"
DOCUMENT = ROOT / "docs/preregistration/TRACK_B_PREREG_v1.md"


def load_registry() -> dict:
    return yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))


def test_track_b_production_pilots_and_unblinding_remain_prohibited() -> None:
    data = load_registry()

    assert data["status"] == "draft_not_frozen"
    assert data["production_authorized"] is False
    assert data["unblinding_authorized"] is False
    assert data["pilot_1k_authorized"] is False
    assert data["pilot_10k_authorized"] is False
    assert data["nature_tier_gate"] == "closed"


def test_all_required_freeze_artifacts_are_explicit_and_honest() -> None:
    artifacts = {
        item["path"]: item["state"] for item in load_registry()["required_freeze_artifacts"]
    }

    assert set(artifacts) == {
        "docs/literature/COMPETITOR_MATRIX_v1.md",
        "docs/literature/NOVELTY_CLEARANCE_v1.md",
        "docs/preregistration/OBSERVATION_FREEZE_v1.md",
        "docs/preregistration/NUCLEAR_PRIOR_FREEZE_v1.md",
        "docs/preregistration/PHYSICS_ENDPOINTS_v1.md",
        "docs/decisions/ADR-SOLVER-FACTORIAL-v1.md",
        "docs/decisions/ADR-FISHER-GATE-v1.md",
        "artifacts/gates/FISHER_GATE_REPORT_v1.md",
    }
    assert artifacts["docs/preregistration/NUCLEAR_PRIOR_FREEZE_v1.md"] == "not_frozen"
    assert artifacts["artifacts/gates/FISHER_GATE_REPORT_v1.md"] == "missing"
    for path, state in artifacts.items():
        if state != "missing":
            assert (ROOT / path).is_file()


def test_registered_boundaries_match_existing_endpoint_and_cost_contracts() -> None:
    boundaries = load_registry()["frozen_null_boundaries"]

    assert boundaries["maximum_absolute_normalized_median_shift"] == 0.1
    assert boundaries["credible_interval_ratio"] == [0.95, 1.05]
    assert boundaries["maximum_in_domain_failure_fraction"] == 0.01
    assert boundaries["hybrid_minimum_high_fidelity_call_reduction"] == 10
    assert boundaries["hybrid_alternative_minimum_wall_time_reduction"] == 5
    assert boundaries["direct_first_maximum_calendar_days"] == 14
    assert boundaries["direct_first_maximum_worker_hours"] == 672


def test_signoffs_and_operational_scientific_boundary_remain_pending() -> None:
    data = load_registry()
    text = DOCUMENT.read_text(encoding="utf-8")

    assert all(value == "pending" for value in data["signoffs"].values())
    assert "PRODUCTION AND UNBLINDING PROHIBITED" in text
    assert "A00 scientific lead: **pending**" in text
    assert "A09 independent validation: **pending**" in text
    assert "Operational authorization does not substitute" in text
