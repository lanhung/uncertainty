from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RUN = (
    ROOT
    / "artifacts/benchmarks/LINX-NATIVE-Q-REPRODUCTION-v2"
    / "run-20260723T102602Z"
)
VALIDATOR = ROOT / "scripts/validate_linx_native_q_reproduction_v2.py"
OUTBOX = ROOT / "artifacts/benchmarks/UQ0-NATIVE-UQ-REPRO-OFFLINE-HEARTBEATS-v2"


def load_validator():
    spec = importlib.util.spec_from_file_location("linx_v2_validator", VALIDATOR)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_v2_artifact_passes_independent_frozen_validator() -> None:
    result = load_validator().validator.validate(
        RUN / "reproduction.json",
        ROOT / "configs/benchmarks/linx_native_q_reproduction_v2.yaml",
    )
    decision = result["decision"]

    assert result["accepted"] is True
    assert result["native_UQ_task_progress_eligible"] is True
    assert result["scalar_rows"] == 42
    assert result["batch_rows"] == 28
    assert all(decision["checks"].values())
    assert decision["plateaus"]["tolerance"][
        "maximum_difference_observation_sigma"
    ] == 0.0006193677328284428
    assert decision["plateaus"]["weak_rate_sampling"][
        "maximum_difference_observation_sigma"
    ] == 0.00022808196589943274


def test_offline_parent_progress_events_are_fail_closed_from_replay() -> None:
    files = sorted(OUTBOX.glob("*.ndjson"))
    assert len(files) == 2
    events = [
        json.loads(line)
        for path in files
        for line in path.read_text(encoding="utf-8").splitlines()
    ]
    assert any(
        event.get("current", 0) > event.get("total", 5)
        for event in events
        if event.get("event") == "progress"
    )
    readme = (OUTBOX / "README.md").read_text(encoding="utf-8")
    assert "do not replay" in readme
    assert "no active UQ0 outbox remains" in readme
