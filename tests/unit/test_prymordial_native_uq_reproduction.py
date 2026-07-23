from __future__ import annotations

import json
import shutil
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

import scripts.run_prymordial_native_uq_reproduction as runner
from scripts.run_prymordial_native_uq_reproduction import (
    DEFAULT_PROTOCOL,
    OUTPUT_FILENAMES,
    RATE_PARAMETER_NAMES,
    _assign_solver_contract,
    add_record_digest,
    atomic_json,
    build_summary,
    canonical_json,
    digest_json,
    draw_manifest_digest,
    generate_draw_manifest,
    load_protocol,
    terminal_records,
    write_draw_manifest,
    write_state,
)
from scripts.validate_prymordial_native_uq_reproduction import (
    validate,
    validate_runtime_environment,
)


def write_jsonl(path: Path, records: list[dict[str, object]]) -> None:
    path.write_bytes(
        b"".join(canonical_json(add_record_digest(record)) + b"\n" for record in records)
    )


def build_synthetic_accepted_run(output_dir: Path) -> None:
    protocol = load_protocol(DEFAULT_PROTOCOL)
    draws = generate_draw_manifest(protocol)
    output_dir.mkdir()
    write_draw_manifest(output_dir / OUTPUT_FILENAMES["draw_manifest"], draws)

    reference = protocol["public_reference"]["exact_row"]
    standardized = np.linspace(-1.0, 1.0, len(draws), dtype=np.float64)
    standardized -= np.mean(standardized)
    standardized /= np.std(standardized, ddof=1)
    yp = float(reference["Yp_BBN"]) + float(reference["sigma_Yp_BBN"]) * standardized
    dh = float(reference["D_over_H"]) - float(reference["sigma_D_over_H"]) * standardized
    raw_results: list[dict[str, object]] = []
    for draw, yp_value, dh_value in zip(draws, yp, dh):
        raw_results.append(
            {
                "schema_version": 1,
                "draw_id": draw["draw_id"],
                "input_record_sha256": draw["record_sha256"],
                "Yp_BBN": float(yp_value),
                "D_over_H": float(dh_value),
                "elapsed_seconds": 1.0,
            }
        )
    write_jsonl(output_dir / OUTPUT_FILENAMES["results"], raw_results)
    (output_dir / OUTPUT_FILENAMES["failures"]).write_text("", encoding="utf-8")
    successes, failures = terminal_records(output_dir)

    source_config = protocol["source"]
    source = {
        "repository": source_config["repository"],
        "revision": source_config["revision"],
        "license": source_config["license"],
        "required_file_sha256": {
            relative: details["sha256"]
            for relative, details in source_config["required_files"].items()
        },
        "tracked_worktree_matches_HEAD": True,
    }
    environment_config = protocol["environment"]
    environment = {
        "python": environment_config["python"],
        "numpy": environment_config["numpy"],
        "scipy": environment_config["scipy"],
        "platform": "Linux-test-platform",
        "precision": environment_config["precision"],
        "backend": environment_config["backend"],
        "lock_path": environment_config["lock_path"],
        "lock_sha256": environment_config["lock_sha256"],
    }
    config_sha256 = __import__("hashlib").sha256(DEFAULT_PROTOCOL.read_bytes()).hexdigest()
    manifest_digest = draw_manifest_digest(draws)
    run_id = digest_json(
        {
            "protocol_sha256": config_sha256,
            "source_revision": source["revision"],
            "draw_manifest_sha256": manifest_digest,
        }
    )
    manifest = {
        "schema_version": 1,
        "protocol_id": protocol["protocol_id"],
        "task_id": protocol["task_id"],
        "run_id": run_id,
        "config_path": str(DEFAULT_PROTOCOL),
        "config_sha256": config_sha256,
        "source": source,
        "environment": environment,
        "draw_manifest_sha256": manifest_digest,
        "output_files": OUTPUT_FILENAMES,
        "created_at_utc": "2026-07-23T00:00:00+00:00",
    }
    manifest["evidence_sha256"] = digest_json(manifest)
    atomic_json(output_dir / OUTPUT_FILENAMES["run_manifest"], manifest)

    prior = protocol["native_prior"]
    central_input = add_record_digest(
        {
            "schema_version": 1,
            "draw_id": -1,
            "seed_entropy": None,
            "seed_spawn_key": [],
            "bit_generator": None,
            "tau_n_seconds": float(prior["neutron_lifetime"]["mean_seconds"]),
            "nuclear_rate_parameter_names": list(RATE_PARAMETER_NAMES),
            "nuclear_rate_q": [0.0] * len(RATE_PARAMETER_NAMES),
        }
    )
    central = {
        "draw_id": -1,
        "input_record_sha256": central_input["record_sha256"],
        "Yp_BBN": float(reference["Yp_BBN"]),
        "D_over_H": float(reference["D_over_H"]),
        "elapsed_seconds": 1.0,
    }
    by_id = {int(record["draw_id"]): record for record in successes}
    repeat_outputs = []
    for draw_id in protocol["execution"]["sentinel_repeat_draw_indices"]:
        original = by_id[int(draw_id)]
        repeat_outputs.append(
            {
                "draw_id": int(draw_id),
                "input_record_sha256": original["input_record_sha256"],
                "Yp_BBN": original["Yp_BBN"],
                "D_over_H": original["D_over_H"],
                "elapsed_seconds": 1.0,
            }
        )
    summary = build_summary(
        protocol=protocol,
        run_id=run_id,
        successes=successes,
        failures=failures,
        controls={"central": central, "sentinel_repeats": repeat_outputs},
    )
    assert summary["accepted"] is True
    atomic_json(output_dir / OUTPUT_FILENAMES["summary"], summary)
    write_state(
        output_dir,
        run_id=run_id,
        expected=len(draws),
        successes=successes,
        failures=failures,
        status="accepted",
    )


@pytest.fixture(scope="module")
def accepted_run(tmp_path_factory: pytest.TempPathFactory) -> Path:
    output_dir = tmp_path_factory.mktemp("prymordial-native") / "run"
    build_synthetic_accepted_run(output_dir)
    return output_dir


def test_prepare_run_initializes_empty_terminal_ledgers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(runner, "validate_source", lambda *_: {"revision": "test"})
    monkeypatch.setattr(runner, "validate_environment", lambda *_: {"python": "test"})
    monkeypatch.setattr(runner, "generate_draw_manifest", lambda *_: [])
    monkeypatch.setattr(runner, "validate_draw_manifest", lambda *_: None)
    monkeypatch.setattr(runner, "draw_manifest_digest", lambda *_: "draws")
    monkeypatch.setattr(runner, "write_state", lambda *args, **kwargs: None)

    runner.prepare_run(
        protocol_path=DEFAULT_PROTOCOL,
        source_root=tmp_path / "source",
        output_dir=tmp_path / "run",
        resume=False,
    )

    assert (tmp_path / "run" / OUTPUT_FILENAMES["results"]).is_file()
    assert (tmp_path / "run" / OUTPUT_FILENAMES["failures"]).is_file()


def test_validator_rejects_numpy_version_drift(monkeypatch: pytest.MonkeyPatch) -> None:
    protocol = load_protocol(DEFAULT_PROTOCOL)
    monkeypatch.setattr(np, "__version__", "0.0-test")
    with pytest.raises(RuntimeError, match="validator NumPy drift"):
        validate_runtime_environment(protocol)


def test_frozen_draw_manifest_is_reproducible_and_63_dimensional() -> None:
    draws = generate_draw_manifest(load_protocol(DEFAULT_PROTOCOL))
    assert len(draws) == 1000
    assert draws[0]["seed_spawn_key"] == [0]
    assert draws[-1]["seed_spawn_key"] == [999]
    assert len(draws[0]["nuclear_rate_q"]) == 63
    assert draws[0]["record_sha256"] == (
        "b9db058bc0efe920f47be347d0b62d2d1164fb03fd1d02fe4d6650e7f52c6bb5"
    )
    assert draws[499]["record_sha256"] == (
        "57def4d99a4de8e6bd00454374cd4a3f80087992fe3f82eaeae8f12f8b1038b2"
    )
    assert draws[999]["record_sha256"] == (
        "cf233d09730e58b3e6086e88d1cf428d4d4f571abb795f170263d62413536d70"
    )


def test_protocol_threshold_cannot_be_relaxed_via_cli_override(tmp_path: Path) -> None:
    altered = tmp_path / "altered.yaml"
    altered.write_text(
        DEFAULT_PROTOCOL.read_text(encoding="utf-8").replace(
            "maximum_failure_fraction: 0.01",
            "maximum_failure_fraction: 0.10",
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="protocol digest drift"):
        load_protocol(altered)


def test_solver_contract_fully_resets_global_inputs() -> None:
    init = SimpleNamespace(Omegabh2_to_eta0b=2.0, reload_count=0)

    def reload_rates() -> None:
        init.reload_count += 1

    init.ReloadKeyRates = reload_rates
    record = generate_draw_manifest(load_protocol(DEFAULT_PROTOCOL))[0]
    _assign_solver_contract(init, record)
    assert init.smallnet_flag is False
    assert init.nacreii_flag is True
    assert init.num_reactions == 63
    assert init.Omegabh2 == 0.0222
    assert init.eta0b == 0.0444
    assert init.DeltaNeff == 0.0
    assert init.NP_nuclear_flag is False
    assert init.NP_nTOp_flag is False
    assert init.reload_count == 1
    assert [getattr(init, name) for name in RATE_PARAMETER_NAMES] == record["nuclear_rate_q"]
    assert all(
        getattr(init, f"NP_delta_{name.removeprefix('p_')}") == 0.0 for name in RATE_PARAMETER_NAMES
    )


def test_independent_validator_accepts_complete_statistical_reproduction(
    accepted_run: Path,
) -> None:
    result = validate(accepted_run)
    assert result["accepted"] is True
    assert result["attempted_draws"] == 1000
    assert result["successful_draws"] == 1000
    assert result["failed_draws"] == 0
    assert result["Yp_sigma_ratio"] == pytest.approx(1.0)
    assert result["D_over_H_sigma_ratio"] == pytest.approx(1.0)


def test_validator_rejects_recomputed_scientific_overclaim(
    accepted_run: Path, tmp_path: Path
) -> None:
    bad = tmp_path / "bad-overclaim"
    shutil.copytree(accepted_run, bad)
    summary_path = bad / OUTPUT_FILENAMES["summary"]
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["scientific_boundary"]["accepted_scientific_prior"] = True
    summary.pop("evidence_sha256")
    summary["evidence_sha256"] = digest_json(summary)
    atomic_json(summary_path, summary)
    with pytest.raises(ValueError, match="boundary drift|overclaims"):
        validate(bad)


def test_validator_rejects_incomplete_terminal_accounting(
    accepted_run: Path, tmp_path: Path
) -> None:
    bad = tmp_path / "bad-terminal-accounting"
    shutil.copytree(accepted_run, bad)
    result_path = bad / OUTPUT_FILENAMES["results"]
    lines = result_path.read_text(encoding="utf-8").splitlines(keepends=True)
    result_path.write_text("".join(lines[:-1]), encoding="utf-8")
    with pytest.raises(ValueError, match="terminal draw accounting is incomplete"):
        validate(bad)


def test_terminal_reader_rejects_duplicate_success_and_failure(
    tmp_path: Path,
) -> None:
    result = {
        "schema_version": 1,
        "draw_id": 7,
        "input_record_sha256": "a" * 64,
        "Yp_BBN": 0.24,
        "D_over_H": 2.5e-5,
        "elapsed_seconds": 1.0,
    }
    failure = {
        "schema_version": 1,
        "draw_id": 7,
        "input_record_sha256": "a" * 64,
        "error_type": "RuntimeError",
        "error_message": "failure",
        "traceback_tail": "traceback",
    }
    write_jsonl(tmp_path / OUTPUT_FILENAMES["results"], [result])
    write_jsonl(tmp_path / OUTPUT_FILENAMES["failures"], [failure])
    with pytest.raises(RuntimeError, match="multiple terminal records"):
        terminal_records(tmp_path)
