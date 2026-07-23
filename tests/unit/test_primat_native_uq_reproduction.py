from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import yaml


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs/benchmarks/primat_native_uq_reproduction_v1.yaml"


def load_module(relative: str):
    path = ROOT / relative
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_protocol_freezes_compiled_c_native_prior_and_c0_boundary() -> None:
    protocol = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    assert protocol["protocol_id"] == "PRIMAT-NATIVE-UQ-REPRODUCTION-v1"
    assert protocol["source"]["revision"] == ("21ff8f39fa18e3937e9fdf386cfa982361bfdfce")
    assert protocol["execution"]["force_backend"] == "c"
    assert protocol["execution"]["prohibited_backends"] == ["python"]
    assert protocol["execution"]["draws"] == 1000
    assert protocol["execution"]["prefix_draws"] == [100, 300, 1000]
    assert protocol["execution"]["serial_replay_draws"] == 16
    assert protocol["native_prior"]["thermonuclear_latents"]["count"] == 12
    boundary = protocol["scientific_boundary"]
    assert boundary["claim_level"] == "C0"
    assert boundary["production_use_authorized"] is False
    assert boundary["project_nuclear_prior_selected"] is False
    assert boundary["counts_as_R0_prior_validation"] is False
    assert boundary["counts_as_UQ1_direct_MC_truth"] is False


def test_runner_protocol_loader_rejects_byte_drift(tmp_path: Path) -> None:
    runner = load_module("scripts/run_primat_native_uq_reproduction.py")
    drifted = tmp_path / "protocol.yaml"
    drifted.write_bytes(CONFIG.read_bytes() + b"\n")
    with pytest.raises(RuntimeError, match="protocol byte drift"):
        runner.require_protocol(drifted)


def test_runner_maps_exact_registered_solver_parameters() -> None:
    runner = load_module("scripts/run_primat_native_uq_reproduction.py")
    protocol, _ = runner.require_protocol(CONFIG)
    assert runner.solver_parameters(protocol) == {
        "Omegabh2": 0.02237,
        "DeltaNeff": 0.0,
        "tau_n": 878.3,
        "std_tau_n": 0.5,
        "tau_n_normalization": True,
        "network": "small",
        "numerical_precision": 1.0e-7,
        "rescale_nuclear_rates": False,
        "QED_corrections": True,
        "nuclear_qed_corrections": True,
        "mc_rate_rescale_cap": 30.0,
        "verbose": False,
        "debug": False,
        "show_progress": False,
    }


def test_prefix_summary_uses_registered_ddof_and_quantiles() -> None:
    runner = load_module("scripts/run_primat_native_uq_reproduction.py")
    values = np.arange(1200, dtype=np.float64).reshape(300, 4) + 1.0
    result = runner.summarize_prefixes(values, [100, 300], [0.025, 0.16, 0.5, 0.84, 0.975])
    first = result["100"]["quantities"]["YPBBN"]
    assert first["mean"] == pytest.approx(float(np.mean(values[:100, 0])))
    assert first["standard_deviation_ddof1"] == pytest.approx(
        float(np.std(values[:100, 0], ddof=1))
    )
    assert first["quantiles"]["0.500"] == pytest.approx(float(np.quantile(values[:100, 0], 0.5)))


def test_checkpoint_loader_fails_closed_on_partial_checkpoint(tmp_path: Path) -> None:
    runner = load_module("scripts/run_primat_native_uq_reproduction.py")
    (tmp_path / "checkpoint.json").write_text("{}", encoding="utf-8")
    with pytest.raises(RuntimeError, match="partial checkpoint"):
        runner.load_checkpoint(
            tmp_path,
            protocol_sha256=runner.EXPECTED_PROTOCOL_SHA256,
            source_revision=runner.EXPECTED_REVISION,
            seed=2026072301,
            params={},
        )


def test_checkpoint_writer_uses_versioned_samples_then_atomic_pointer(
    tmp_path: Path,
) -> None:
    runner = load_module("scripts/run_primat_native_uq_reproduction.py")
    samples = np.arange(12, dtype=np.float64).reshape(3, 4) + 1.0

    class FakeMC:
        backend = "c"

        def quantity_names(self) -> list[str]:
            return list(runner.EXPECTED_QUANTITIES)

        def samples_array(self) -> np.ndarray:
            return samples

        def __getitem__(self, name: str) -> SimpleNamespace:
            index = self.quantity_names().index(name)
            return SimpleNamespace(central=float(index + 1))

    runner.write_checkpoint(
        tmp_path,
        FakeMC(),
        protocol_sha256=runner.EXPECTED_PROTOCOL_SHA256,
        source_revision=runner.EXPECTED_REVISION,
        seed=2026072301,
        params={"network": "small"},
    )
    state = json.loads((tmp_path / "checkpoint.json").read_text())
    assert state["samples_file"] == "checkpoint_samples_3.npy"
    stored = np.load(tmp_path / state["samples_file"], allow_pickle=False)
    assert np.array_equal(stored, samples)
    assert state["samples_sha256"] == runner.sha256(tmp_path / "checkpoint_samples_3.npy")


def test_validator_rejects_missing_artifact(tmp_path: Path) -> None:
    validator = load_module("scripts/validate_primat_native_uq_reproduction.py")
    with pytest.raises(FileNotFoundError):
        validator.validate(tmp_path / "missing.json")


def test_validator_derived_table_tolerance_is_cross_platform_but_strict() -> None:
    validator = load_module("scripts/validate_primat_native_uq_reproduction.py")
    expected = np.asarray([[1.0, 2.0]], dtype=np.float64)
    validator.compare_array(expected * (1.0 + 4.0e-15), expected, "cross-platform")
    with pytest.raises(ValueError, match="does not reproduce raw samples"):
        validator.compare_array(expected * (1.0 + 1.0e-8), expected, "material drift")


def test_validator_rejects_digest_or_scope_tamper(tmp_path: Path) -> None:
    validator = load_module("scripts/validate_primat_native_uq_reproduction.py")
    artifact = {
        "schema_version": 1,
        "artifact_id": "PRIMAT-NATIVE-UQ-REPRODUCTION-v1",
        "task_id": "UQ0-NATIVE-UQ-REPRO",
        "status": "completed_upstream_native_compiled_C_calibration",
        "scientific_scope": {"production_authorized": True},
    }
    artifact["evidence_sha256"] = validator.digest_json(artifact)
    path = tmp_path / "artifact.json"
    path.write_text(json.dumps(artifact), encoding="utf-8")
    with pytest.raises((KeyError, ValueError)):
        validator.validate(path)

    artifact["scientific_scope"]["production_authorized"] = False
    path.write_text(json.dumps(artifact), encoding="utf-8")
    with pytest.raises(ValueError, match="digest"):
        validator.validate(path)
