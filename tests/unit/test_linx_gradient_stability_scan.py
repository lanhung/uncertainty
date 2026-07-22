from pathlib import Path

import pytest
import yaml

from scripts.linx_gradient_stability_scan import (
    evaluate_decision,
    expand_acceptance_points,
    five_point_central,
    scaled_difference,
)
from scripts import linx_gradient_stability_scan


ROOT = Path(__file__).resolve().parents[2]


def load(relative: str) -> dict:
    return yaml.safe_load((ROOT / relative).read_text(encoding="utf-8"))


def test_acceptance_point_expansion_is_unique_and_frozen() -> None:
    points = expand_acceptance_points(
        load("configs/benchmarks/linx_gradient_stability_v1.yaml"),
        load("configs/physics/parameter_schema.yaml"),
        load("configs/data/cmb_data_v1.yaml"),
        load("configs/physics/neutron_lifetime_v1.yaml"),
    )
    by_id = {point["point_id"]: point for point in points}

    assert len(points) == 15
    assert len(by_id) == 15
    assert by_id["fiducial"]["physical"] == {
        "delta_neff": 0.0,
        "omega_b_h2": 0.02237,
        "tau_n_seconds": 878.3,
    }
    assert by_id["axis_delta_neff_p0p5"]["physical"]["delta_neff"] == 0.05
    assert by_id["axis_omega_b_h2_m1"]["physical"]["omega_b_h2"] == pytest.approx(0.02222)
    assert by_id["axis_tau_n_seconds_p1"]["physical"]["tau_n_seconds"] == pytest.approx(878.7)
    assert sum(point["point_id"].startswith("corner_") for point in points) == 8


def test_five_point_central_is_exact_for_quartic_vector_function() -> None:
    def function(values: list[float]) -> list[float]:
        x, y = values
        return [x**4 + 2.0 * y, 3.0 * x - y**3]

    derivative_x = five_point_central(function, [1.5, -0.25], 0, 0.1)
    derivative_y = five_point_central(function, [1.5, -0.25], 1, 0.1)

    assert derivative_x == pytest.approx([13.5, 3.0], rel=1.0e-12, abs=1.0e-12)
    assert derivative_y == pytest.approx([2.0, -0.1875], rel=1.0e-12, abs=1.0e-12)


def test_scaled_difference_uses_stable_unit_floor_and_rejects_nonfinite() -> None:
    assert scaled_difference([2.0, 0.5], [1.0, 0.0]) == pytest.approx(1.0)
    assert scaled_difference([100.5], [100.0]) == pytest.approx(0.005)
    assert math_is_inf(scaled_difference([float("nan")], [1.0]))


def math_is_inf(value: float) -> bool:
    return value == float("inf")


def passing_record() -> dict:
    return {
        "status": "ok",
        "forward_finite": True,
        "jacobian_finite": True,
        "silent_nonfinite_count": 0,
        "scaled_repeat_drift": 0.0,
        "ad_mode_scaled_difference": 0.01,
        "ad_fd_scaled_difference": 0.01,
        "fd_plateau_scaled_difference": 0.01,
    }


def acceptance() -> dict:
    return load("configs/benchmarks/linx_gradient_stability_v1.yaml")["acceptance"]


def test_decision_requires_every_record_and_all_frozen_metrics() -> None:
    records = [passing_record() for _ in range(45)]

    result = evaluate_decision(records, acceptance(), 45, structured_failures=0)

    assert result["passed"] is True
    assert result["numerical_gradient_status"] == "accepted"
    assert result["finite_forward_fraction"] == 1.0
    assert result["finite_jacobian_fraction"] == 1.0
    assert all(result["checks"].values())


def test_decision_fails_closed_on_missing_record_or_fd_mismatch() -> None:
    records = [passing_record() for _ in range(44)]
    records[0]["ad_fd_scaled_difference"] = 0.0200001

    result = evaluate_decision(records, acceptance(), 45, structured_failures=1)

    assert result["passed"] is False
    assert result["numerical_gradient_status"] == "not_accepted"
    assert result["checks"]["all_records_present"] is False
    assert result["checks"]["ad_fd_difference"] is False
    assert result["checks"]["structured_failures"] is False


def test_preflight_mode_prints_json_without_creating_output(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    config = ROOT / "configs/benchmarks/linx_gradient_stability_v1.yaml"
    inventory = tmp_path / "inventory.json"
    inventory.write_text('{"node_name":"test"}\n', encoding="utf-8")
    lock = ROOT / "environments/linx-v0.1.2/uv.lock"
    source = tmp_path / "source"
    source.mkdir()
    output = tmp_path / "must-not-exist"
    scan = load("configs/benchmarks/linx_gradient_stability_v1.yaml")
    loaded = {
        "scan": scan,
        "parameter_schema": load("configs/physics/parameter_schema.yaml"),
        "cmb": load("configs/data/cmb_data_v1.yaml"),
        "neutron": load("configs/physics/neutron_lifetime_v1.yaml"),
        "revision": scan["source_revision"],
    }
    monkeypatch.setattr(linx_gradient_stability_scan, "_preflight", lambda args: (loaded, {}))
    monkeypatch.setattr(
        "sys.argv",
        [
            "linx-gradient",
            "--preflight",
            "--config",
            str(config),
            "--source-dir",
            str(source),
            "--inventory",
            str(inventory),
            "--environment-lock",
            str(lock),
            "--output-dir",
            str(output),
        ],
    )

    assert linx_gradient_stability_scan.main() == 0
    report = yaml.safe_load(capsys.readouterr().out)
    assert report["status"] == "ok"
    assert report["acceptance_point_count"] == 15
    assert output.exists() is False
