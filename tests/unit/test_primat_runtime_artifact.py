import hashlib
import json
from pathlib import Path

import pytest
import yaml

from scripts.why_not_benchmark import summarize


ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "artifacts/benchmarks/WHY-NOT-EXISTING-SOLVERS-v1/W2-PRIMAT/run-20260722T0535Z"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(name: str) -> dict:
    return json.loads((RUN / name).read_text(encoding="utf-8"))


def test_primat_runtime_manifest_is_bound_to_registered_inputs() -> None:
    manifest = load_json("run_manifest.json")
    protocol_path = ROOT / "configs/benchmarks/why_not_existing_solvers_v1.yaml"
    schema_path = ROOT / "configs/physics/parameter_schema_standard_bbn_v1.yaml"
    lock_path = ROOT / "environments/solver-cpu/uv.lock"
    protocol = yaml.safe_load(protocol_path.read_text(encoding="utf-8"))

    assert manifest["status"] == "complete"
    assert manifest["scientific_use"] == "registered_standard_fiducial_runtime_slice_only"
    assert manifest["source_revision"] == protocol["baselines"]["W2-PRIMAT"]["revision"]
    assert manifest["config_sha256"] == sha256(protocol_path)
    assert manifest["parameter_schema_sha256"] == sha256(schema_path)
    assert manifest["environment_lock_sha256"] == sha256(lock_path)
    assert manifest["repetitions"] == protocol["execution"]["warm_repetitions"]
    assert manifest["batch_sizes"] == protocol["execution"]["batch_sizes"]
    assert manifest["node_name"] == "autodl-westb-01"
    assert len(manifest["hardware_inventory_sha256"]) == 64

    registry = yaml.safe_load((RUN.parent / "RESULT_REGISTRY_v1.yaml").read_text(encoding="utf-8"))
    assert registry["registered_runtime_slices"] == 1
    assert registry["slices"][0]["run"] == RUN.name
    assert registry["full_baseline_status"] == "incomplete"
    assert registry["why_not_conclusion"] == "undetermined"


def test_every_registered_timing_observation_and_failure_is_preserved() -> None:
    records = [
        json.loads(line)
        for line in (RUN / "timings.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    warm = [record for record in records if record["kind"] == "warm_batch"]
    scalar = [record for record in warm if record["batch_size"] == 1]
    batch = [record for record in warm if record["batch_size"] == 64]

    assert len(records) == 62
    assert len(scalar) == 30
    assert len(batch) == 30
    assert sum(record["successful_points"] for record in warm) == 1950
    assert all(record["status"] == "ok" for record in warm)
    assert (RUN / "failures.jsonl").read_bytes() == b""

    summary = load_json("runtime_summary.json")
    assert summary["maximum_absolute_repeat_drift"] == 0.0
    assert summarize([record["elapsed_seconds"] for record in scalar])["median"] == pytest.approx(
        summary["timings_seconds"]["warm_batch_1"]["median"]
    )
    assert summarize([record["elapsed_seconds"] for record in batch])["p95"] == pytest.approx(
        summary["timings_seconds"]["warm_batch_64"]["p95"]
    )


def test_runtime_slice_does_not_fabricate_posterior_or_gpu_evidence() -> None:
    posterior = load_json("posterior_metrics.json")
    resources = load_json("resource_report.json")

    assert posterior["status"] == "not_run"
    assert "old likelihood assets" in posterior["reason"]
    assert resources["failure_count"] == 0
    assert resources["gpu_hours"] == 0.0
    assert resources["wall_seconds"] > 0
    assert resources["estimated_cost_cny"] > 0
