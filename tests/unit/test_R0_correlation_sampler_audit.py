from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.validate_R0_correlation_sampler_audit import validate


ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = ROOT / "artifacts/priors/R0-CORRELATION-SAMPLER-AUDIT-v1/audit.json"


def test_frozen_correlation_sampler_audit_validates() -> None:
    summary = validate(ARTIFACT, ROOT)
    assert summary["model_records"] == 35
    assert summary["unique_matrix_sha256"] == 34
    assert summary["all_model_checks_passed"] is True
    assert summary["fixed_seed_replay_passed_models"] == 35
    assert summary["nearest_PSD_projection_used_models"] == 0


def test_validator_rejects_artifact_tamper_before_claim_use(
    tmp_path: Path,
) -> None:
    artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    artifact["claim_boundary"]["actual_ETR25_cross_reaction_covariance_inferred"] = True
    bad = tmp_path / "audit.json"
    bad.write_text(json.dumps(artifact), encoding="utf-8")
    with pytest.raises(ValueError, match="SHA256 drift"):
        validate(bad, ROOT)
