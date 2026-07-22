from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
SCHEMA = ROOT / "configs/physics/parameter_schema.yaml"
WHY_NOT = ROOT / "configs/benchmarks/why_not_existing_solvers_v1.yaml"


def test_standard_bbn_fiducial_inherits_frozen_inputs() -> None:
    schema = yaml.safe_load(SCHEMA.read_text(encoding="utf-8"))
    cmb = yaml.safe_load((ROOT / "configs/data/cmb_data_v1.yaml").read_text(encoding="utf-8"))
    neutron = yaml.safe_load(
        (ROOT / "configs/physics/neutron_lifetime_v1.yaml").read_text(encoding="utf-8")
    )
    values = schema["standard_bbn_fiducial"]["values"]

    assert values["omega_b_h2"] == cmb["main_stage"]["mean"]
    assert values["tau_n_seconds"] == neutron["scenarios"]["N0"]["mean"]
    assert values["delta_neff"] == 0.0
    assert values["kappa10"] == 0.0
    assert schema["track_b_gate_status"] == "closed"


def test_unresolved_extension_parameters_cannot_be_silently_used() -> None:
    schema = yaml.safe_load(SCHEMA.read_text(encoding="utf-8"))
    parameters = schema["parameters"]

    assert parameters["kappa10"]["freeze_status"] == "standard_model_null_only"
    assert parameters["tensor_tilt"]["prior"]["status"] == "not_frozen"
    assert parameters["reheating_temperature"]["prior"]["status"] == "not_frozen"
    assert len(schema["adapter_aliases"]["prohibited_unresolved_mappings"]) == 2
    assert schema["open_blockers"]


def test_why_not_standard_scenario_points_to_available_frozen_subset() -> None:
    protocol = yaml.safe_load(WHY_NOT.read_text(encoding="utf-8"))
    standard = next(item for item in protocol["scenarios"] if item["id"] == "standard_fiducial")

    assert standard["parameter_source"] == "configs/physics/parameter_schema.yaml"
    assert standard["parameter_set"] == "standard_bbn_fiducial"
    assert standard["availability"] == "available_standard_bbn_subset"
