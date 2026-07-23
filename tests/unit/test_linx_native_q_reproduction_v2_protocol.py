from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
V1 = ROOT / "configs/benchmarks/linx_native_q_reproduction_v1.yaml"
V2 = ROOT / "configs/benchmarks/linx_native_q_reproduction_v2.yaml"


def load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_v2_tightens_numerics_without_relaxing_acceptance() -> None:
    v1 = load(V1)
    v2 = load(V2)
    old = {case["id"]: case for case in v1["numerical_cases"]}
    new = {case["id"]: case for case in v2["numerical_cases"]}

    assert v2["reproduction_id"] == "LINX-NATIVE-Q-REPRODUCTION-v2"
    assert v2["source"] == v1["source"]
    assert v2["q_contract"] == v1["q_contract"]
    assert v2["claim_boundary"] == v1["claim_boundary"]
    assert v2["acceptance"] == v1["acceptance"]
    assert new["A_candidate"]["rtol"] < old["A_candidate"]["rtol"]
    assert new["A_candidate"]["atol"] < old["A_candidate"]["atol"]
    assert new["A_candidate"]["sampling_nTOp"] > old["A_candidate"]["sampling_nTOp"]
    assert new["B_tolerance"]["rtol"] == old["A_candidate"]["rtol"]
    assert new["C_sampling"]["sampling_nTOp"] == old["A_candidate"]["sampling_nTOp"]
    assert all(case["max_steps"] == 32768 for case in new.values())
    assert v2["acceptance"]["maximum_plateau_difference_observation_sigma"] == 0.001


def test_v2_wrappers_pin_artifact_and_config_identity() -> None:
    runner = (ROOT / "scripts/run_linx_native_q_reproduction_v2.py").read_text(encoding="utf-8")
    validator = (ROOT / "scripts/validate_linx_native_q_reproduction_v2.py").read_text(
        encoding="utf-8"
    )
    digest = "f8415100950cecaedecc7baed30a5d3f903833a1247922911c5de5c0748e93e3"

    assert "LINX-NATIVE-Q-REPRODUCTION-v2" in runner
    assert "LINX-NATIVE-Q-REPRODUCTION-v2" in validator
    assert digest in runner
    assert digest in validator
