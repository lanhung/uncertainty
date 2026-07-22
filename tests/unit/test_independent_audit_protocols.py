from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[2]


def load(path: str) -> dict:
    return yaml.safe_load((ROOT / path).read_text(encoding="utf-8"))


def test_standard_challenge_grid_is_derived_from_frozen_inputs() -> None:
    grid = load("configs/benchmarks/why_not_standard_challenge_grid_v1.yaml")
    cmb = load("configs/data/cmb_data_v1.yaml")["main_stage"]
    neutron = load("configs/physics/neutron_lifetime_v1.yaml")["scenarios"]
    cases = {case["id"]: case for case in grid["cases"]}

    assert grid["status"] == "protocol_frozen_measurements_pending"
    assert set(grid["baselines"]) == {"W0-LINX", "W1-PRYM", "W2-PRIMAT", "W3-ABCMB"}
    assert cases["omega_b_minus_2sigma"]["omega_b_h2"] == pytest.approx(
        cmb["mean"] - 2 * cmb["sigma"]
    )
    assert cases["omega_b_plus_2sigma"]["omega_b_h2"] == pytest.approx(
        cmb["mean"] + 2 * cmb["sigma"]
    )
    assert cases["tau_n_n0_minus_2sigma"]["tau_n_seconds"] == pytest.approx(
        neutron["N0"]["mean"] - 2 * neutron["N0"]["sigma"]
    )
    assert cases["tau_n_n0_plus_2sigma"]["tau_n_seconds"] == pytest.approx(
        neutron["N0"]["mean"] + 2 * neutron["N0"]["sigma"]
    )
    assert cases["tau_n_bottle_n1"]["tau_n_seconds"] == neutron["N1"]["mode"]
    assert cases["tau_n_beam_n2"]["tau_n_seconds"] == neutron["N2"]["mean"]
    assert grid["acceptance"]["cross_baseline_abundance_differences_are_descriptive_only"]


def test_linx_gradient_protocol_separates_acceptance_and_extreme_diagnostic() -> None:
    scan = load("configs/benchmarks/linx_gradient_stability_v1.yaml")

    assert scan["source_revision"] == "ec2e9d2ca455e8204137e884da29f5dd13a638fa"
    assert scan["nuclear_rates_q"] == "all_zero"
    assert set(scan["paths"]) == {
        "background_only_delta_neff",
        "frozen_background_abundance_eta_tau",
        "full_end_to_end_three_coordinate_jacobian",
    }
    assert scan["finite_difference"]["method"] == "five_point_central"
    assert scan["acceptance"]["finite_jacobian_fraction"] == 1.0
    assert scan["acceptance"]["maximum_ad_fd_scaled_difference"] == 0.02
    assert scan["diagnostic_only_upstream_challenge"]["affects_acceptance_domain"] is False


def test_abcmb_protocol_forbids_unavailable_formal_claims() -> None:
    audit = load("configs/benchmarks/abcmb_full_component_audit_v1.yaml")

    assert audit["backend"] == "jax_cpu"
    assert len(audit["spectra_cases"]) == 5
    assert audit["toy_fisher"]["status"] == ("authorized_interface_smoke_not_formal_fisher_gate")
    assert audit["synthetic_recovery"]["points"] == 41
    assert "formal_FISH-01_or_G0_to_G3_credit" in audit["prohibited_current_claims"]
    assert "HMC_or_NUTS_acceptance" in audit["prohibited_current_claims"]
    assert audit["resource_limits"]["dry_run_required_before_lmax_2500"] is True


def test_offline_heartbeat_protocol_requires_safe_replay_and_gate_invariance() -> None:
    protocol = load("configs/ops/offline_heartbeat_e2e_v1.yaml")

    assert protocol["phase"] == "EXEC"
    assert protocol["endpoint_during_run"] == "http://127.0.0.1:1"
    assert protocol["replay_mode"] == "dry_run_then_explicit_apply"
    assert protocol["replay_safety"]["exec_phase_tasks_only"] is True
    assert protocol["replay_safety"]["atomic_acknowledged_prefix_removal"] is True
    assert "http_4xx" in protocol["replay_safety"]["stop_and_preserve_tail_on"]
    assert protocol["acceptance_checks"][-1] == ("science_gate_unchanged_and_snapshot_pushed")


def test_all_new_trackers_are_execution_only() -> None:
    plan = load("plan/plan.yaml")
    tasks = {task["id"]: task for task in plan["tasks"]}
    expected = {
        "EXEC-ABCMB-FULL-AUDIT": (4, "components"),
        "EXEC-LINX-GRADIENT": (4, "groups"),
        "EXEC-STANDARD-CHALLENGE": (4, "baselines"),
        "EXEC-HEARTBEAT-OFFLINE-E2E-v1": (8, "checks"),
    }

    for task_id, (total, unit) in expected.items():
        assert tasks[task_id]["phase"] == "EXEC"
        assert tasks[task_id]["total"] == total
        assert tasks[task_id]["unit"] == unit
