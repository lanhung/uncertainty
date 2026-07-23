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


def test_gp_protocol_is_fail_closed_for_abundance_rerun() -> None:
    protocol = yaml.safe_load(
        (ROOT / "configs/benchmarks/gp_deuterium_prior_structure_v1.yaml").read_text()
    )
    assert protocol["source"]["arxiv"] == "2604.16600v1"
    assert protocol["acceptance_boundary"]["native_UQ_task_progress_eligible"] is False
    for field in (
        "analysis_code_public",
        "fitted_hyperparameters_public",
        "posterior_draws_public",
        "experimental_data_bundle_public",
        "random_seed_public",
    ):
        assert protocol["source"][field] is False


def test_gp_protocol_captures_three_coherent_function_priors() -> None:
    protocol = yaml.safe_load(
        (ROOT / "configs/benchmarks/gp_deuterium_prior_structure_v1.yaml").read_text()
    )
    structure = protocol["prior_structure"]
    assert set(structure["reactions"]) == {"ddn", "ddp", "dpg"}
    assert structure["reactions"]["dpg"]["latent_space"] == "log_S_factor"
    assert structure["draw_contract"]["object"] == "coherent_S_factor_curve"
    assert structure["draw_contract"]["independent_temperature_bin_noise"] == "prohibited"


def test_gp_validator_rejects_missing_artifact(tmp_path: Path) -> None:
    validator = load_module("scripts/validate_gp_deuterium_prior_structure.py")
    with pytest.raises(FileNotFoundError):
        validator.validate(tmp_path / "missing.json")


def test_committed_gp_structure_is_valid_but_not_progress_eligible() -> None:
    validator = load_module("scripts/validate_gp_deuterium_prior_structure.py")
    result = validator.validate(
        ROOT / "artifacts/benchmarks/GP-DEUTERIUM-PRIOR-STRUCTURE-v1/structure.json"
    )
    assert result["structure_capture_accepted"] is True
    assert result["native_UQ_task_progress_eligible"] is False
    assert result["missing_reproduction_input_count"] == 5
