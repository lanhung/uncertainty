from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[2]


def load_module(relative: str):
    path = ROOT / relative
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_protocol_freezes_public_sources_and_c0_boundary() -> None:
    protocol = yaml.safe_load(
        (ROOT / "configs/benchmarks/sensitivity_atlas_R0_slice_v1.yaml").read_text()
    )
    assert protocol["task_id"] == "UQ0-NATIVE-UQ-REPRO"
    assert protocol["published_object"]["revision"] == ("d3ea1838d9450673698f07b7c6b8971efb87d0fd")
    assert protocol["solver"]["revision"] == ("725d8a8db3ad5ea2630580d825c9d0d69ed76533")
    boundary = protocol["scientific_boundary"]
    assert boundary["claim_level"] == "C0_public_calibration_reproduction_only"
    assert boundary["accepted_scientific_prior"] is False
    assert boundary["production_authorized"] is False
    assert boundary["novelty_claim"] is False


def test_protocol_contains_exact_r0_slice() -> None:
    protocol = yaml.safe_load(
        (ROOT / "configs/benchmarks/sensitivity_atlas_R0_slice_v1.yaml").read_text()
    )
    assert [item["native_id"] for item in protocol["solver"]["reactions"]] == [
        "dpHe3g",
        "ddHe3n",
        "ddtp",
    ]
    assert protocol["solver"]["q_values"] == [-1.0, 0.0, 1.0]
    assert set(protocol["published_reference"]["rows"]) == {
        "dpHe3g",
        "ddHe3n",
        "ddtp",
    }


def test_validator_rejects_missing_artifact(tmp_path: Path) -> None:
    validator = load_module("scripts/validate_sensitivity_atlas_R0_slice.py")
    with pytest.raises(FileNotFoundError):
        validator.validate(tmp_path / "missing.json")


def test_committed_execution_is_integral_but_not_progress_eligible() -> None:
    validator = load_module("scripts/validate_sensitivity_atlas_R0_slice.py")
    result = validator.validate(
        ROOT / "artifacts/benchmarks/SENSITIVITY-ATLAS-R0-SLICE-v1/artifact.json"
    )
    assert result["accepted"] is False
    assert result["native_UQ_task_progress_eligible"] is False
    assert result["acceptance_failures"] == [
        "central_reference_mismatch:ddHe3n:Li7H",
        "central_reference_mismatch:ddtp:Li7H",
        "central_reference_mismatch:dpHe3g:Li7H",
        "derivative_sign_mismatch:dpHe3g:Yp",
    ]
