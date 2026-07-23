from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import pytest

from scripts.run_prymordial_R0_mapping_regression import (
    MappingContractError,
    validate_external_draw_contract,
    validate_temperature,
)
from scripts.validate_prymordial_R0_mapping_regression import validate


ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = ROOT / "artifacts" / "priors" / "PRYMORDIAL-R0-MAPPING-REGRESSION-v1" / "regression.json"


def test_frozen_prymordial_mapping_regression_validates() -> None:
    result = validate(ARTIFACT)
    assert result["reaction_count"] == 3
    assert result["q_count"] == 5
    assert result["forward_rows"] == 14985
    assert result["all_three_mappings_unique"] is True
    assert result["duplicate_shift_guard_passed"] is True
    assert result["sequential_draw_contamination_observed"] is False


def test_validator_rejects_scientific_overclaim(tmp_path: Path) -> None:
    artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    artifact["scientific_scope"]["accepted_scientific_prior"] = True
    bad = tmp_path / "regression.json"
    bad.write_text(json.dumps(artifact), encoding="utf-8")
    with pytest.raises(ValueError, match="digest mismatch|overclaims"):
        validate(bad)


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (
            lambda artifact: artifact["source"].__setitem__(
                "repository", "https://example.invalid/evil"
            ),
            "repository",
        ),
        (
            lambda artifact: artifact["reactions"][0]["table"].__setitem__("sha256", "0" * 64),
            "table contract",
        ),
        (
            lambda artifact: artifact["reactions"][0]["probe_grid"].__setitem__("sha256", "0" * 64),
            "probe-grid",
        ),
        (
            lambda artifact: artifact["reactions"][0].__setitem__("trace_sha256", "0" * 64),
            "trace provenance",
        ),
        (
            lambda artifact: artifact["configuration"].__setitem__("interpolation", "cubic"),
            "interpolation",
        ),
        (
            lambda artifact: artifact["acceptance"].__setitem__("absolute_tolerance", 1.0),
            "absolute acceptance",
        ),
    ],
)
def test_validator_rejects_provenance_drift_after_digest_recalculation(
    tmp_path: Path,
    mutate: Callable[[dict[str, object]], None],
    message: str,
) -> None:
    from scripts.validate_prymordial_R0_mapping_regression import digest_json

    artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    mutate(artifact)
    artifact.pop("evidence_sha256")
    artifact["evidence_sha256"] = digest_json(artifact)
    bad = tmp_path / "regression.json"
    bad.write_text(json.dumps(artifact), encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        validate(bad)


def test_temperature_contract_accepts_boundaries_and_converts_to_kelvin() -> None:
    assert (
        validate_temperature(
            "dpHe3g",
            0.001,
            unit="T9",
            minimum_t9=0.001,
            maximum_t9=10.0,
        )
        == 1.0e6
    )
    assert (
        validate_temperature(
            "dpHe3g",
            10.0,
            unit="T9",
            minimum_t9=0.001,
            maximum_t9=10.0,
        )
        == 1.0e10
    )


@pytest.mark.parametrize(
    ("value", "unit", "code"),
    [
        (0.0009, "T9", "temperature_out_of_bounds"),
        (10.1, "T9", "temperature_out_of_bounds"),
        (float("nan"), "T9", "nonfinite_temperature"),
        (1.0e6, "K", "unsupported_temperature_unit"),
    ],
)
def test_temperature_contract_returns_structured_rejections(
    value: float, unit: str, code: str
) -> None:
    with pytest.raises(MappingContractError) as caught:
        validate_temperature(
            "dpHe3g",
            value,
            unit=unit,
            minimum_t9=0.001,
            maximum_t9=10.0,
        )
    assert caught.value.code == code
    assert caught.value.as_record()["accepted"] is False


def test_external_draw_guard_accepts_only_external_q_representation() -> None:
    validate_external_draw_contract(
        np_nuclear_flag=False,
        deltas={
            "NP_delta_dpHe3g": 0.0,
            "NP_delta_ddHe3n": 0.0,
            "NP_delta_ddtp": 0.0,
        },
    )
    with pytest.raises(MappingContractError, match="duplicate_nuclear_shift_representation"):
        validate_external_draw_contract(
            np_nuclear_flag=True,
            deltas={
                "NP_delta_dpHe3g": 0.25,
                "NP_delta_ddHe3n": 0.0,
                "NP_delta_ddtp": 0.0,
            },
        )
