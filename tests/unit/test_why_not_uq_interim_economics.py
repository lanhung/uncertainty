from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.build_why_not_uq_interim_economics import build
from scripts.validate_why_not_uq_interim_economics import validate


ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = ROOT / "artifacts/benchmarks/WHY-NOT-UQ-INTERIM-ECONOMICS-v1/package.json"


def test_frozen_interim_uq_economics_validates() -> None:
    assert validate(ARTIFACT, ROOT) == {
        "baselines": 4,
        "reference_arithmetic_paths": 8,
        "reference_arithmetic_scenarios": 24,
        "why_not_conclusion": "undetermined",
        "progress_credit_memos": 0,
    }


def test_builder_reproduces_frozen_payload() -> None:
    assert build(ROOT) == json.loads(ARTIFACT.read_text(encoding="utf-8"))


def test_validator_rejects_manufactured_direct_solver_decision(
    tmp_path: Path,
) -> None:
    artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    artifact["decision"]["direct_solver_sufficient"] = True
    bad = tmp_path / "package.json"
    bad.write_text(json.dumps(artifact), encoding="utf-8")
    with pytest.raises(ValueError, match="artifact SHA256 drift"):
        validate(bad, ROOT)
