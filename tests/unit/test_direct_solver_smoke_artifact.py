import hashlib
import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = ROOT / "artifacts/solver-build/DIRECT_SOLVER_SMOKE_v1.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_direct_solver_smoke_is_traceable_and_does_not_accept_nan_gradient() -> None:
    result = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    registration = yaml.safe_load(
        (ROOT / "configs/benchmarks/why_not_existing_solvers_v1.yaml").read_text(encoding="utf-8")
    )

    assert result["scientific_use"] == (
        "direct_solver_source_smoke_not_registered_repeated_benchmark"
    )
    assert result["status"] == "partial_pass_with_linx_gradient_failure"

    linx = result["results"]["W0-LINX"]
    assert linx["revision"] == registration["baselines"]["W0-LINX"]["revision"]
    assert linx["forward_reference_max_absolute_percent_difference"] < 0.3
    assert linx["gradient"]["status"] == "failed_nan"
    assert linx["gradient"]["finite_component_count"] < linx["gradient"]["component_count"]
    assert linx["gradient"]["use_for_gradient_or_hmc_baseline"] is False
    assert linx["gradient"]["upstream_process_exit_code"] == 0
    assert all(value > 0 for value in linx["timings_seconds"].values())

    prym = result["results"]["W1-PRYM"]
    assert prym["revision"] == registration["baselines"]["W1-PRYM"]["revision"]
    assert prym["small_network"]["status"] == "passed"
    assert prym["large_network"]["status"] == "passed"
    assert prym["small_network"]["elapsed_seconds"] > 0
    assert prym["large_network"]["elapsed_seconds"] > 0

    for solver in (linx, prym):
        raw_log = ROOT / solver["raw_log"]
        assert raw_log.is_file()
        assert sha256(raw_log) == solver["raw_log_sha256"]
