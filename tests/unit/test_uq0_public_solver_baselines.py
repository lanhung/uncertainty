import json
from pathlib import Path

import pytest
import yaml

from scripts.validate_uq0_solver_baselines import sha256, validate_registry


ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "configs/solvers/public_bbn_baselines_UQ0_v1.yaml"


def test_three_pinned_public_forward_paths_pass_the_uq0_evidence_contract() -> None:
    report = validate_registry(REGISTRY, ROOT)

    assert report["status"] == "pass"
    assert report["accepted_path_count"] == 3
    assert {record["path_id"] for record in report["paths"]} == {
        "UQ0-S6-LINX-key-PRIMAT-2023-v1",
        "UQ0-S4-PRyMordial-small-PRIMAT-like-v1",
        "UQ0-S8-PRIMAT-small-C-v1",
    }


@pytest.mark.parametrize(
    ("card_name", "result_path", "expected_y_p", "expected_d_over_h"),
    [
        (
            "UQ0-S6-LINX-key-PRIMAT-2023-v1.yaml",
            "artifacts/numerical/LINX-CONVERGENCE-RERUN-v4/run-20260722T0722Z/scan_results.json",
            0.24665653167658091,
            2.4417232840590098e-5,
        ),
        (
            "UQ0-S4-PRyMordial-small-PRIMAT-like-v1.yaml",
            "artifacts/benchmarks/WHY-NOT-EXISTING-SOLVERS-v1/W1-PRYM/run-20260722T0753Z/runtime_summary.json",
            0.2468834991108598,
            2.444116205595043e-5,
        ),
        (
            "UQ0-S8-PRIMAT-small-C-v1.yaml",
            "artifacts/benchmarks/WHY-NOT-EXISTING-SOLVERS-v1/W2-PRIMAT/run-20260722T0535Z/runtime_summary.json",
            0.24695513077748688,
            2.4447361728164994e-5,
        ),
    ],
)
def test_card_outputs_are_bound_to_hashed_solver_results(
    card_name: str,
    result_path: str,
    expected_y_p: float,
    expected_d_over_h: float,
) -> None:
    card_path = ROOT / "configs/solvers/cards" / card_name
    card = yaml.safe_load(card_path.read_text(encoding="utf-8"))
    result_record = card["evidence"]["result"]

    assert result_record["path"] == result_path
    assert sha256(ROOT / result_path) == result_record["sha256"]
    assert card["outputs"]["Y_p"]["value"] == pytest.approx(expected_y_p)
    assert card["outputs"]["D_over_H"]["value"] == pytest.approx(expected_d_over_h)

    payload = json.loads((ROOT / result_path).read_text(encoding="utf-8"))
    if card["matrix_id"] == "S6":
        candidate = payload["cases"]["production_candidate"]
        abundances = candidate["scalar_abundances"]
    else:
        abundances = payload["abundances"]
    assert abundances["YPBBN"] == pytest.approx(expected_y_p)
    assert abundances["DoH"] == pytest.approx(expected_d_over_h)


def test_registry_scope_does_not_promote_old_challenges_or_production_readiness() -> None:
    registry = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    joined = "\n".join(registry["prohibitions"])

    assert "paused W0-W3 standard challenge" in joined
    assert "production-ready" in joined
    assert "R0 nuisance adapter" in joined
