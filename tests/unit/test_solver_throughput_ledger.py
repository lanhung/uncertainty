import csv
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
LEDGER = ROOT / "docs/compute/solver_throughput.csv"


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_solver_throughput_is_derived_from_committed_timings() -> None:
    with LEDGER.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))

    assert len(rows) == 4
    assert {(row["baseline"], int(row["batch_size"])) for row in rows} == {
        ("W0-LINX", 1),
        ("W0-LINX", 64),
        ("W2-PRIMAT", 1),
        ("W2-PRIMAT", 64),
    }

    for row in rows:
        batch_size = int(row["batch_size"])
        summary = json.loads((ROOT / row["source_summary"]).read_text(encoding="utf-8"))
        records = _jsonl(ROOT / row["source_timings"])
        matching = [
            record
            for record in records
            if record.get("kind") == "warm_batch"
            and record.get("status") == "ok"
            and record.get("batch_size") == batch_size
        ]
        stats = summary["timings_seconds"][f"warm_batch_{batch_size}"]

        assert len(matching) == int(row["repetitions"]) == 30
        assert {record["execution_mode"] for record in matching} == {row["execution_mode"]}
        assert sum(record["successful_points"] for record in matching) == int(
            row["successful_points"]
        )
        assert float(row["median_seconds_per_batch"]) == pytest.approx(stats["median"])
        assert float(row["p95_seconds_per_batch"]) == pytest.approx(stats["p95"])
        assert float(row["median_seconds_per_point"]) == pytest.approx(stats["median"] / batch_size)
        assert float(row["p95_seconds_per_point"]) == pytest.approx(stats["p95"] / batch_size)
        assert int(row["failure_count"]) == 0
        assert row["scientific_scope"] == "standard_fiducial_runtime_slice_only"


def test_active_w1_is_not_prematurely_recorded() -> None:
    text = LEDGER.read_text(encoding="utf-8")

    assert "W1-PRYM" not in text
    assert "run-20260722T0753Z" not in text
