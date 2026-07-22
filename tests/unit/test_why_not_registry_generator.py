from pathlib import Path
import subprocess
import sys

import pytest
import yaml

from scripts.generate_why_not_result_registry import generate_registry
from scripts.validate_why_not_runtime import ValidationError


ROOT = Path(__file__).resolve().parents[2]
BENCHMARK_ROOT = ROOT / "artifacts/benchmarks/WHY-NOT-EXISTING-SOLVERS-v1"


@pytest.mark.parametrize(
    ("baseline", "run"),
    [
        ("W0-LINX", "run-20260722T0605Z"),
        ("W1-PRYM", "run-20260722T0753Z"),
        ("W2-PRIMAT", "run-20260722T0535Z"),
        ("W3-ABCMB", "run-20260722T1118Z"),
    ],
)
def test_generator_reproduces_committed_runtime_registries(baseline: str, run: str) -> None:
    generated = generate_registry(ROOT, BENCHMARK_ROOT / baseline / run)
    committed = yaml.safe_load(
        (BENCHMARK_ROOT / baseline / "RESULT_REGISTRY_v1.yaml").read_text(encoding="utf-8")
    )

    assert generated == committed
    assert generated["full_baseline_status"] == "incomplete"
    assert generated["why_not_conclusion"] == "undetermined"


def test_generator_refuses_unvalidated_partial_run(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="missing runtime artifacts"):
        generate_registry(ROOT, tmp_path)


def test_registry_policy_covers_every_frozen_baseline() -> None:
    policy = yaml.safe_load(
        (ROOT / "configs/benchmarks/why_not_result_registry_policy_v1.yaml").read_text(
            encoding="utf-8"
        )
    )

    assert set(policy["baselines"]) == {"W0-LINX", "W1-PRYM", "W2-PRIMAT", "W3-ABCMB"}
    assert policy["scientific_boundary"] == "runtime_registry_only_full_baseline_incomplete"
    assert all(item["limitations"] for item in policy["baselines"].values())


def test_generator_direct_script_execution_works_outside_repo(tmp_path: Path) -> None:
    output = tmp_path / "registry.yaml"
    run = BENCHMARK_ROOT / "W2-PRIMAT" / "run-20260722T0535Z"

    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/generate_why_not_result_registry.py"),
            "--repo-root",
            str(ROOT),
            "--run-dir",
            str(run),
            "--output",
            str(output),
        ],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert output.is_file()
    assert yaml.safe_load(output.read_text(encoding="utf-8"))["baseline"] == "W2-PRIMAT"
