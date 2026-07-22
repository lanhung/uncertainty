import subprocess
import sys
from pathlib import Path

import pytest

from scripts.why_not_standard_challenge_grid import (
    expected_cases,
    maximum_repeat_drift,
    validate_cases,
)


def test_expected_cases_are_derived_without_extension_coordinates() -> None:
    cmb = {"main_stage": {"mean": 0.02237, "sigma": 0.00015}}
    neutron = {
        "scenarios": {
            "N0": {"mean": 878.3, "sigma": 0.4},
            "N1": {"mode": 877.82},
            "N2": {"mean": 887.7},
        }
    }

    cases = expected_cases(cmb, neutron)

    assert len(cases) == 7
    assert cases["omega_b_minus_2sigma"]["omega_b_h2"] == pytest.approx(0.02207)
    assert cases["omega_b_plus_2sigma"]["omega_b_h2"] == pytest.approx(0.02267)
    assert cases["tau_n_beam_n2"]["tau_n_seconds"] == 887.7
    assert {case["delta_neff"] for case in cases.values()} == {0.0}


def test_case_validation_rejects_post_freeze_value_or_order_changes() -> None:
    expected = {
        "a": {"omega_b_h2": 0.02, "tau_n_seconds": 878.0, "delta_neff": 0.0},
        "b": {"omega_b_h2": 0.03, "tau_n_seconds": 878.0, "delta_neff": 0.0},
    }
    configured = [{"id": key, **value} for key, value in expected.items()]

    assert validate_cases(configured, expected) == configured
    with pytest.raises(ValueError, match="IDs or order"):
        validate_cases(list(reversed(configured)), expected)
    changed = [dict(case) for case in configured]
    changed[0]["omega_b_h2"] += 1.0e-5
    with pytest.raises(ValueError, match="differs"):
        validate_cases(changed, expected)


def test_repeat_drift_checks_every_output_and_repetition() -> None:
    outputs = [
        {"YPBBN": 0.25, "DoH": 2.5e-5},
        {"YPBBN": 0.2501, "DoH": 2.5e-5},
    ]

    assert maximum_repeat_drift(outputs) == pytest.approx(0.0001)


def test_direct_cli_help_works_outside_repository(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    completed = subprocess.run(
        [sys.executable, str(root / "scripts/why_not_standard_challenge_grid.py"), "--help"],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert "--preflight" in completed.stdout
