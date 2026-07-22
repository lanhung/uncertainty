from pathlib import Path

import pytest

from scripts.validate_why_not_runtime import ValidationError, validate_run


ROOT = Path(__file__).resolve().parents[2]
BENCHMARK_ROOT = ROOT / "artifacts/benchmarks/WHY-NOT-EXISTING-SOLVERS-v1"


@pytest.mark.parametrize(
    ("baseline", "run", "expected_mode"),
    [
        ("W0-LINX", "run-20260722T0605Z", "native_batch_mode"),
        ("W2-PRIMAT", "run-20260722T0535Z", "sequential_batch_mode"),
    ],
)
def test_existing_runtime_slices_pass_generic_integrity_validation(
    baseline: str, run: str, expected_mode: str
) -> None:
    report = validate_run(ROOT, BENCHMARK_ROOT / baseline / run)

    assert report["validation_status"] == "passed"
    assert report["scientific_use"] == "artifact_integrity_only_not_scientific_acceptance"
    assert report["successful_warm_points"] == 1950
    assert report["timed_warm_points_expected"] == 1950
    assert report["failure_records"] == 0
    assert expected_mode in report["checks"]
    assert report["timings"]["scalar_median_seconds"] > 0
    assert report["timings"]["batch_64_median_seconds_per_point"] > 0


def test_validator_rejects_missing_artifact_set(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="missing runtime artifacts"):
        validate_run(ROOT, tmp_path)
