import hashlib
import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = ROOT / "artifacts/environments"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name: str) -> dict:
    return json.loads((ARTIFACTS / name).read_text(encoding="utf-8"))


def test_general_worker_smokes_match_checked_in_locks() -> None:
    solver = load("environment-solver-cpu-autodl-westb-01.json")
    train = load("environment-train-gpu-autodl-westb-01.json")

    assert solver["lock_sha256"] == sha256(ROOT / "environments/solver-cpu/uv.lock")
    assert solver["fixed_point"]["jax_x64"] is True
    assert solver["fixed_point"]["max_abs_difference"] == 0.0

    assert train["lock_sha256"] == sha256(ROOT / "environments/train-gpu/uv.lock")
    assert train["fixed_point"]["cuda_available"] is True
    assert train["fixed_point"]["device"] == "cuda"
    assert train["packages"]["torch"] == "2.12.1+cu130"


def test_competitor_smokes_match_sources_and_locks() -> None:
    manifest = yaml.safe_load(
        (ROOT / "manifests/software/why_not_baselines_v1.yaml").read_text(encoding="utf-8")
    )
    artifact_names = {
        "W0-LINX": "environment-W0-LINX-autodl-westb-01.json",
        "W1-PRYM": "environment-W1-PRYM-autodl-westb-01.json",
        "W2-PRIMAT": "environment-W2-PRIMAT-autodl-westb-01.json",
        "W3-ABCMB": "environment-W3-ABCMB-autodl-westb-01.json",
    }
    for baseline, artifact_name in artifact_names.items():
        artifact = load(artifact_name)
        registration = manifest["baselines"][baseline]
        assert artifact["status"] == "source_smoke_passed"
        assert artifact["scientific_use"] == "environment_acceptance_only_not_a_benchmark"
        assert artifact["source"]["revision"] == registration["revision"]
        assert registration["environment_status"] == "worker_source_smoke_passed"

    assert load(artifact_names["W0-LINX"])["lock_sha256"] == sha256(
        ROOT / "environments/linx-v0.1.2/uv.lock"
    )
    assert load(artifact_names["W3-ABCMB"])["lock_sha256"] == sha256(
        ROOT / "environments/abcmb-v0.3.1/uv.lock"
    )
