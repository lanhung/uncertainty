from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.validate_primat_R0_reverse_regression import validate
from worker.primat_rate_draw import apply_variations_safely


ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = ROOT / "artifacts/priors/PRIMAT-R0-REVERSE-REGRESSION-v1/regression.json"


def test_frozen_reverse_regression_validates() -> None:
    assert validate(ARTIFACT) == {
        "reactions": 3,
        "temperature_probes": 1076,
        "reverse_rows": 16140,
        "reverse_ratio_exclusions": 5760,
        "log_shift_exclusions": 5760,
        "cache_cases": 6,
        "wrapper_guard_cases": 12,
        "cap_active_within_tolerance_rows": 90,
        "cap_active_actual_LT_probe_rows": 0,
        "cache_guard_required": True,
    }


def test_validator_rejects_hidden_cache_regression(tmp_path: Path) -> None:
    artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    artifact["acceptance"]["upstream_cache_invalidation_required"] = False
    bad = tmp_path / "regression.json"
    bad.write_text(json.dumps(artifact), encoding="utf-8")
    with pytest.raises(ValueError, match="cache regression"):
        validate(bad)


@pytest.mark.parametrize(
    ("section", "field", "value", "message"),
    [
        ("configuration", "mc_rate_rescale_cap", 999.0, "rescale cap"),
        ("configuration", "nuclear_qed_corrections", False, "nuclear-QED"),
        (
            "acceptance",
            "unclamped_log_shift_identity_max_abs_tolerance",
            1.0,
            "acceptance tolerance",
        ),
    ],
)
def test_validator_rejects_configuration_or_tolerance_drift(
    tmp_path: Path,
    section: str,
    field: str,
    value: object,
    message: str,
) -> None:
    artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    artifact[section][field] = value
    bad = tmp_path / "regression.json"
    bad.write_text(json.dumps(artifact), encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        validate(bad)


class FakeNetwork:
    def __init__(self) -> None:
        self._cache_T_t = 0.8e9
        self._cache_clamp = True
        self.applied = False

    def apply_variations(self, config: object) -> None:
        self.applied = config is not None


def test_safe_apply_invalidates_both_cache_keys() -> None:
    network = FakeNetwork()
    apply_variations_safely(network, SimpleNamespace())
    assert network.applied
    assert network._cache_T_t is None
    assert network._cache_clamp is None


def test_safe_apply_refuses_unknown_cache_contract() -> None:
    network = SimpleNamespace(apply_variations=lambda _config: None)
    with pytest.raises(RuntimeError, match="cache contract changed"):
        apply_variations_safely(network, SimpleNamespace())


class FakeWrapper:
    def __init__(self) -> None:
        self._mt_net = FakeNetwork()
        self._lt_net = FakeNetwork()
        self.applied = False

    def apply_variations(self, config: object) -> None:
        self.applied = config is not None


def test_safe_apply_invalidates_both_wrapper_networks() -> None:
    wrapper = FakeWrapper()
    apply_variations_safely(wrapper, SimpleNamespace())
    assert wrapper.applied
    assert wrapper._mt_net._cache_T_t is None
    assert wrapper._mt_net._cache_clamp is None
    assert wrapper._lt_net._cache_T_t is None
    assert wrapper._lt_net._cache_clamp is None
