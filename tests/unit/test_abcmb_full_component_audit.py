from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/abcmb_full_component_audit.py"
CONFIG = ROOT / "configs/benchmarks/abcmb_full_component_audit_v1.yaml"


def load_module():
    spec = importlib.util.spec_from_file_location("abcmb_full_component_audit", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_protocol() -> dict:
    return yaml.safe_load(CONFIG.read_text(encoding="utf-8"))


def test_frozen_protocol_is_supported_and_defaults_to_safe_s0() -> None:
    module = load_module()
    protocol = load_protocol()
    cases = module.validate_protocol(protocol)

    assert set(cases) == {
        "S0_quick_default",
        "S1_table_unlensed",
        "S2_table_lensed",
        "S3_linx_unlensed",
        "S4_linx_lensed",
    }
    assert protocol["resource_limits"]["dry_run_case"] == "S0_quick_default"
    assert cases["S0_quick_default"]["lmax"] == 500
    assert (
        module.parse_args(["--source-dir", "/tmp/source", "--output-dir", "/tmp/output"]).cases
        is None
    )


def test_protocol_rejects_unregistered_linx_rate_coordinates() -> None:
    module = load_module()
    protocol = load_protocol()
    protocol["spectra_cases"][3]["nuclear_rates_q"] = "sampled"

    with pytest.raises(ValueError, match="only all-zero technical rates"):
        module.validate_protocol(protocol)


def test_high_lmax_requires_bound_accepted_s0_evidence(tmp_path: Path) -> None:
    module = load_module()
    protocol = load_protocol()
    config_hash = module.sha256(CONFIG)
    evidence = tmp_path / "results.json"
    evidence.write_text(
        json.dumps(
            {
                "audit_id": protocol["audit_id"],
                "config_sha256": config_hash,
                "source_revision": protocol["source_revision"],
                "spectra": [{"case_id": "S0_quick_default", "status": "accepted"}],
            }
        ),
        encoding="utf-8",
    )

    bound = module.validate_dry_run_evidence(evidence, protocol, config_hash)
    assert bound["case_id"] == "S0_quick_default"
    assert bound["sha256"] == module.sha256(evidence)

    payload = json.loads(evidence.read_text(encoding="utf-8"))
    payload["spectra"][0]["status"] = "not_accepted"
    evidence.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="accepted S0"):
        module.validate_dry_run_evidence(evidence, protocol, config_hash)


def test_unimplemented_components_are_explicit_not_run() -> None:
    module = load_module()
    components = module.component_statuses(True)

    assert components["spectra"]["status"] == "evaluated"
    assert components["gradient"]["status"] == "not_run"
    assert components["toy_fisher"]["status"] == "not_run"
    assert components["synthetic_recovery"]["status"] == "not_run"
    assert components["hmc_nuts"]["status"] == "not_run"


def test_preflight_writes_required_artifacts_without_running_spectra(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    module = load_module()
    source = tmp_path / "source"
    source.mkdir()
    output = tmp_path / "output"
    protocol = load_protocol()

    monkeypatch.setattr(
        module,
        "preflight_checks",
        lambda *_args: {
            "status": "passed",
            "source_revision": protocol["source_revision"],
            "bundled_linx_tree": protocol["bundled_linx_tree"],
        },
    )

    return_code = module.main(
        [
            "--preflight",
            "--config",
            str(CONFIG),
            "--source-dir",
            str(source),
            "--output-dir",
            str(output),
        ]
    )

    assert return_code == 0
    for name in module.REQUIRED_ARTIFACTS:
        assert (output / name).is_file()
    results = json.loads((output / "results.json").read_text(encoding="utf-8"))
    assert results["status"] == "preflight_complete"
    assert results["spectra"] == []
    assert results["components"]["gradient"]["status"] == "not_run"
    assert (output / "failures.jsonl").read_bytes() == b""
