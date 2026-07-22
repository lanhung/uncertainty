from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "configs/physics/physics_endpoints_v1.yaml"
DOCUMENT = ROOT / "docs/preregistration/PHYSICS_ENDPOINTS_v1.md"


def test_primary_endpoints_and_null_boundaries_are_machine_readable() -> None:
    data = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    endpoints = data["physical_primary_endpoints"]

    assert endpoints["detectable_volume_ratio"]["expression"] == (
        "V_detectable_full / V_detectable_baseline"
    )
    assert endpoints["normalized_parameter_shift"]["null_effect_boundary_absolute"] == 0.1
    assert endpoints["credible_interval_ratio"]["null_effect_interval"] == [0.95, 1.05]
    assert endpoints["posterior_or_exclusion_topology"]["null_effect_category"] == "unchanged"
    assert data["track_b_gate_status"] == "closed"


def test_unavailable_contracts_do_not_receive_fabricated_thresholds() -> None:
    data = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    endpoints = data["physical_primary_endpoints"]

    assert endpoints["detectable_volume_ratio"]["decision_threshold"]["status"].startswith(
        "pending_"
    )
    assert endpoints["sensitivity_reordering"]["success_threshold"]["status"].startswith("pending_")
    assert endpoints["nuclear_value_of_information"]["success_threshold"]["status"].startswith(
        "pending_"
    )
    assert "A00_scientific_signoff" in data["open_blockers"]


def test_endpoint_document_preserves_negative_results_and_pending_signoff() -> None:
    text = DOCUMENT.read_text(encoding="utf-8")

    assert "Crossing no effect threshold is a valid result" in text
    assert "Pilot-10k unauthorized" in text
    assert "A00 scientific lead: pending" in text
    assert "Track B remains NOT FROZEN" in text
