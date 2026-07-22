import hashlib
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
SCHEMA = ROOT / "configs/physics/parameter_schema.yaml"
WHY_NOT = ROOT / "configs/benchmarks/why_not_existing_solvers_v1.yaml"
HISTORICAL_SCHEMA = ROOT / "configs/physics/parameter_schema_standard_bbn_v1.yaml"


def test_historical_standard_bbn_schema_is_byte_frozen() -> None:
    assert hashlib.sha256(HISTORICAL_SCHEMA.read_bytes()).hexdigest() == (
        "61dc9c3ec1fdc9eb455f9ed64ad604a49d801e2b7de361db8db74a883b8c3c9e"
    )


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
    assert "kappa10" not in values
    assert schema["production_gate_status"] == "closed_pending_UQ2_GATE_REPORT"


def test_optional_extensions_do_not_enter_active_rate_uq_scope() -> None:
    schema = yaml.safe_load(SCHEMA.read_text(encoding="utf-8"))
    optional = schema["optional_nonstandard_parameters"]

    assert optional["kappa10"]["freeze_status"] == "inactive_optional"
    assert optional["kappa10"]["backend_mappings"]["status"] == (
        "not_required_for_active_R0_R1_work"
    )
    assert optional["tensor_tilt"]["prior"]["status"] == "not_frozen"
    assert optional["reheating_temperature"]["prior"]["status"] == "not_frozen"
    assert schema["parameter_families"]["nuclear_rate_z_R0"]["freeze_status"] == (
        "scope_frozen_numerical_priors_pending"
    )
    assert len(schema["adapter_aliases"]["prohibited_silent_mappings"]) == 2
    assert schema["open_blockers"]


def test_why_not_standard_scenario_points_to_available_frozen_subset() -> None:
    protocol = yaml.safe_load(WHY_NOT.read_text(encoding="utf-8"))
    standard = next(item for item in protocol["scenarios"] if item["id"] == "standard_fiducial")

    assert standard["parameter_source"] == "configs/physics/parameter_schema.yaml"
    assert standard["parameter_set"] == "standard_bbn_fiducial"
    assert standard["availability"] == "available_standard_bbn_subset"
