from __future__ import annotations

import json
from pathlib import Path

import pytest

import scripts.validate_linx_R0_mapping_regression as linx_validator
from scripts.validate_linx_R0_mapping_regression import validate


ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = ROOT / "artifacts/priors/LINX-R0-MAPPING-REGRESSION-v1/regression.json"


def write_mutation(tmp_path: Path, artifact: dict[str, object]) -> Path:
    path = tmp_path / "regression.json"
    path.write_text(json.dumps(artifact), encoding="utf-8")
    return path


def test_frozen_linx_R0_mapping_regression_validates() -> None:
    assert validate(ARTIFACT) == {
        "reactions": 3,
        "unique_q_indices": 3,
        "rate_rows": 4485,
        "reverse_ratio_defined_rows": 2430,
        "reverse_underflow_excluded_rows": 2055,
        "out_of_grid_rows": 30,
        "consecutive_draw_rows": 96,
        "consecutive_draw_reverse_underflow_excluded_rows": 24,
        "acceptance_passes": True,
    }


def test_validator_rejects_duplicate_R0_q_index(tmp_path: Path) -> None:
    artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    artifact["reactions"][1]["nuclear_rates_q_index_zero_based"] = 1
    with pytest.raises(ValueError, match="unique q-index mapping"):
        validate(write_mutation(tmp_path, artifact))


def test_validator_rejects_hidden_reverse_underflow(tmp_path: Path) -> None:
    artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    excluded = next(
        row
        for reaction in artifact["reactions"]
        for row in reaction["rows"]
        if row["reverse_ratio_exclusion_reason"] == "zero_or_subnormal_reverse"
    )
    excluded["reverse_ratio_exclusion_reason"] = None
    with pytest.raises(ValueError, match="underflow exclusion"):
        validate(write_mutation(tmp_path, artifact))


def test_validator_rejects_out_of_grid_execution_drift(tmp_path: Path) -> None:
    artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    artifact["reactions"][0]["out_of_grid"][0]["forward"] = 1.0
    with pytest.raises(ValueError, match="out-of-grid zero behavior"):
        validate(write_mutation(tmp_path, artifact))


def test_validator_rejects_consecutive_draw_cache_regression(
    tmp_path: Path,
) -> None:
    artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    artifact["reactions"][0]["consecutive_draw_sequence"]["rows"][0]["forward"] *= 1.01
    with pytest.raises(ValueError, match="consecutive-draw forward residual"):
        validate(write_mutation(tmp_path, artifact))


@pytest.mark.parametrize(
    ("section", "field", "value", "message"),
    [
        (
            "scope",
            "abundance_level_UQ_run",
            True,
            "overstates scientific scope",
        ),
        (
            "interface_contract",
            "mutable_cache_attributes_detected",
            ["rate_cache"],
            "interface contract",
        ),
        (
            "acceptance",
            "forward_relative_tolerance",
            1.0,
            "acceptance contract",
        ),
        (
            "source",
            "repository",
            "https://example.invalid/evil",
            "provenance",
        ),
        (
            "environment",
            "interpax",
            "0.0.0",
            "environment",
        ),
    ],
)
def test_validator_rejects_scope_interface_or_tolerance_drift(
    tmp_path: Path,
    section: str,
    field: str,
    value: object,
    message: str,
) -> None:
    artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    artifact[section][field] = value
    with pytest.raises(ValueError, match=message):
        validate(write_mutation(tmp_path, artifact))


def test_validator_rejects_frozen_package_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    package_path = (
        ROOT / "artifacts/priors/NUCLEAR-STAGE0-R0-LINX-KEY-RECOMMENDED-v1" / "package.json"
    )
    package = json.loads(package_path.read_text(encoding="utf-8"))
    package["coordinate"]["grid"][0] *= 2.0
    fake_root = tmp_path / "repository"
    fake_package = (
        fake_root / "artifacts/priors/NUCLEAR-STAGE0-R0-LINX-KEY-RECOMMENDED-v1" / "package.json"
    )
    fake_package.parent.mkdir(parents=True)
    fake_package.write_text(json.dumps(package), encoding="utf-8")
    monkeypatch.setattr(linx_validator, "REPOSITORY_ROOT", fake_root)
    with pytest.raises(ValueError, match="package SHA256 drift"):
        validate(ARTIFACT)
