from __future__ import annotations

import hashlib
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs/benchmarks/why_not_existing_solvers_v1.yaml"
ADR = ROOT / "docs/decisions/ADR-WHY-NOT-001.md"
FETCHER = ROOT / "scripts/fetch_why_not_baselines.sh"
SOURCE_MANIFEST = ROOT / "manifests/software/why_not_baselines_v1.yaml"


def test_why_not_protocol_has_all_mandatory_competitors_and_stop_rules() -> None:
    data = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))

    assert set(data["baselines"]) == {"W0-LINX", "W1-PRYM", "W2-PRIMAT", "W3-ABCMB"}
    assert data["execution"]["precision"] == "float64"
    assert data["execution"]["warm_repetitions"] >= 30
    assert data["acceptance"]["maximum_absolute_normalized_median_shift"] == 0.1
    assert data["acceptance"]["credible_interval_ratio"] == [0.95, 1.05]
    assert data["decision_rules"]["hybrid_necessity"]["minimum_high_fidelity_call_reduction"] == 10
    assert data["decision_rules"]["reject_hybrid_on_fidelity_failure"] is True
    assert data["source_fetcher"] == "scripts/fetch_why_not_baselines.sh"

    fetcher = FETCHER.read_text(encoding="utf-8")
    for baseline in data["baselines"].values():
        assert baseline["revision"] in fetcher


def test_why_not_protocol_does_not_fabricate_results() -> None:
    data = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    results = data["current_results"]

    assert data["status"] == "protocol_frozen_measurements_pending"
    assert results["measured_baselines"] == 0
    assert results["conclusion"] == "undetermined"

    text = ADR.read_text(encoding="utf-8")
    assert "No baseline has yet completed the full registered measurement set" in text
    assert "closes protocol discretion, not `P0-WHY-NOT-01`" in text


def test_incompatible_jax_baselines_require_separate_locks() -> None:
    data = yaml.safe_load(SOURCE_MANIFEST.read_text(encoding="utf-8"))
    finding = data["shared_environment_finding"]

    assert data["baselines"]["W0-LINX"]["dependency_evidence"]["fast_jax"] == "0.4.28"
    assert data["baselines"]["W3-ABCMB"]["dependency_evidence"]["jax"] == "0.8.1"
    assert finding["current_solver_cpu_jax"] == "0.7.2"
    assert finding["compatible_with_exact_W0"] is False
    assert finding["compatible_with_exact_W3"] is False

    protocol = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    locks = protocol["execution"]["environment_locks"]
    assert locks["W0-LINX"] != locks["W3-ABCMB"]
    for key in ("W0-LINX", "W3-ABCMB"):
        assert (ROOT / locks[key]).is_file()

    for key in ("W0-LINX", "W3-ABCMB"):
        baseline = data["baselines"][key]
        digest = hashlib.sha256((ROOT / baseline["environment"]).read_bytes()).hexdigest()
        assert digest == baseline["environment_sha256"]

    linx = data["baselines"]["W0-LINX"]
    sidecar = (ROOT / linx["sidecar_requirements"]).read_text(encoding="utf-8")
    assert "interpax==0.3.1" in sidecar
    for digest in linx["sidecar_hashes"]:
        assert f"sha256:{digest}" in sidecar
