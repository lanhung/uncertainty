from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/validate_native_uq_external_blockers.py"
AUDIT = ROOT / "artifacts/benchmarks/NATIVE-UQ-EXTERNAL-BLOCKERS-v1/audit.json"
ATLAS = ROOT / "artifacts/benchmarks/SENSITIVITY-ATLAS-R0-SLICE-v1/artifact.json"
GP = ROOT / "artifacts/benchmarks/GP-DEUTERIUM-PRIOR-STRUCTURE-v1/structure.json"


def load_module():
    spec = importlib.util.spec_from_file_location("native_uq_external_blockers", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_committed_external_blocker_audit_is_fail_closed() -> None:
    result = load_module().validate(AUDIT, ATLAS, GP)

    assert result == {
        "accepted_baselines": 3,
        "atlas_status": "externally_blocked",
        "audit_valid": True,
        "gp_status": "externally_blocked",
        "native_uq_task_progress_eligible": False,
        "production_authorized": False,
        "task_total": 5,
    }


def test_audit_rejects_progress_or_threshold_overclaim(tmp_path: Path) -> None:
    module = load_module()
    original = json.loads(AUDIT.read_text(encoding="utf-8"))

    for name, mutate in (
        (
            "progress",
            lambda payload: payload["native_uq_task_progress"].update({"after_audit": 5}),
        ),
        (
            "threshold",
            lambda payload: payload["scientific_boundary"].update(
                {"acceptance_thresholds_changed": True}
            ),
        ),
    ):
        payload = copy.deepcopy(original)
        mutate(payload)
        path = tmp_path / f"{name}.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        try:
            module.validate(path, ATLAS, GP)
        except ValueError:
            pass
        else:
            raise AssertionError(f"{name} overclaim was accepted")


def test_audit_rejects_tampered_linked_evidence(tmp_path: Path) -> None:
    module = load_module()
    payload = json.loads(ATLAS.read_text(encoding="utf-8"))
    payload["acceptance_passes"] = True
    path = tmp_path / "atlas.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    try:
        module.validate(AUDIT, path, GP)
    except ValueError as exc:
        assert "digest drift" in str(exc)
    else:
        raise AssertionError("tampered atlas evidence was accepted")
