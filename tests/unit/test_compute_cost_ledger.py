import csv
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
LEDGER = ROOT / "docs/compute/cost_ledger.csv"
DAILY = ROOT / "docs/compute/daily_status/2026-07-22.md"


def test_cost_ledger_is_derived_from_committed_resource_reports() -> None:
    with LEDGER.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))

    assert len(rows) == 6
    assert len({row["run_id"] for row in rows}) == len(rows)
    for row in rows:
        report_path = ROOT / row["source_report"]
        report = json.loads(report_path.read_text(encoding="utf-8"))
        assert float(row["worker_hours"]) == pytest.approx(report["worker_hours"])
        assert float(row["cpu_core_hours"]) == pytest.approx(report["cpu_core_hours"])
        assert float(row["gpu_hours"]) == pytest.approx(report["gpu_hours"])
        assert float(row["hourly_price_cny"]) == pytest.approx(report["hourly_price_cny"])
        assert float(row["estimated_cost_cny"]) == pytest.approx(report["estimated_cost_cny"])

    assert sum(float(row["worker_hours"]) for row in rows) == pytest.approx(0.6404460398428555)
    assert sum(float(row["cpu_core_hours"]) for row in rows) == pytest.approx(0.8404997832111111)
    assert sum(float(row["gpu_hours"]) for row in rows) == 0.0
    assert sum(float(row["estimated_cost_cny"]) for row in rows) == pytest.approx(
        1.8444845947474242
    )


def test_daily_status_keeps_active_evidence_and_cost_unaccepted() -> None:
    text = DAILY.read_text(encoding="utf-8")

    assert "run-20260722T0753Z" in text
    assert "no W1\nlabel is accepted" in text
    assert "W1 cost is still accruing" in text
    assert "does not yet support restart" in text
    assert "Do not use either bjb1 node" in text
    assert "No public endpoint, password, token, SSH key" in text
