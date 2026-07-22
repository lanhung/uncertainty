#!/usr/bin/env python3
"""Offline validation for an archived heartbeat/lease E2E evidence bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

try:
    from scripts.replay_heartbeat_outbox import ReplayError, validate_outbox
except ImportError:  # direct script execution
    from replay_heartbeat_outbox import ReplayError, validate_outbox

REQUIRED_FILES = {
    "run_manifest.json",
    "runner.log",
    "checkpoint-midrun.json",
    "checkpoint-final.json",
    "run_metadata.json",
    "lease-midrun.json",
    "outbox-before-replay.ndjson",
    "replay_report.json",
    "resource_report.json",
    "SHA256SUMS",
}
HEX256 = re.compile(r"^[0-9a-f]{64}$")


def _json_object(path: Path, errors: list[str]) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        errors.append(f"invalid JSON {path.name}: {exc}")
        return {}
    if not isinstance(value, dict):
        errors.append(f"{path.name} must contain a JSON object")
        return {}
    return value


def _nonnegative_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0


def _validate_checksums(root: Path, errors: list[str]) -> dict[str, str]:
    checksum_path = root / "SHA256SUMS"
    checksums: dict[str, str] = {}
    try:
        lines = checksum_path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        errors.append(f"cannot read SHA256SUMS: {exc}")
        return checksums
    for line_number, line in enumerate(lines, start=1):
        parts = line.split("  ", 1)
        if len(parts) != 2 or not HEX256.fullmatch(parts[0]):
            errors.append(f"invalid SHA256SUMS line {line_number}")
            continue
        name = parts[1]
        candidate = Path(name)
        if candidate.is_absolute() or ".." in candidate.parts:
            errors.append(f"unsafe checksum path: {name}")
            continue
        target = root / candidate
        if not target.is_file():
            errors.append(f"checksum target missing: {name}")
            continue
        actual = hashlib.sha256(target.read_bytes()).hexdigest()
        if actual != parts[0]:
            errors.append(f"checksum mismatch: {name}")
        checksums[name] = parts[0]
    return checksums


def validate_bundle(root: str | Path) -> dict[str, Any]:
    directory = Path(root)
    errors: list[str] = []
    if directory.is_symlink() or not directory.is_dir():
        return {"status": "not_accepted", "errors": [f"not a bundle directory: {directory}"]}
    missing = sorted(name for name in REQUIRED_FILES if not (directory / name).is_file())
    if missing:
        errors.append("missing required files: " + ", ".join(missing))
        return {"status": "not_accepted", "errors": errors}

    manifest = _json_object(directory / "run_manifest.json", errors)
    mid = _json_object(directory / "checkpoint-midrun.json", errors)
    final = _json_object(directory / "checkpoint-final.json", errors)
    metadata = _json_object(directory / "run_metadata.json", errors)
    lease = _json_object(directory / "lease-midrun.json", errors)
    replay = _json_object(directory / "replay_report.json", errors)
    resources = _json_object(directory / "resource_report.json", errors)
    checksums = _validate_checksums(directory, errors)

    task_id = manifest.get("task_id")
    run_id = manifest.get("run_id")
    if manifest.get("schema_version") != 1:
        errors.append("run_manifest schema_version must be 1")
    if manifest.get("phase") != "EXEC":
        errors.append("run_manifest phase must be EXEC")
    if manifest.get("scientific_gate_credit") != 0:
        errors.append("run_manifest scientific_gate_credit must be 0")
    if not isinstance(task_id, str) or not task_id:
        errors.append("run_manifest task_id must be non-empty")
    if not isinstance(run_id, str) or not run_id:
        errors.append("run_manifest run_id must be non-empty")

    try:
        outbox = validate_outbox(directory / "outbox-before-replay.ndjson")
    except ReplayError as exc:
        errors.append(f"invalid archived outbox: {exc}")
        outbox = None
    if outbox is not None:
        if outbox.task_id != task_id or outbox.run_id != run_id:
            errors.append("archived outbox identity does not match run_manifest")
        if replay.get("archive_sha256") != outbox.sha256:
            errors.append("replay archive_sha256 does not match archived outbox")
        if checksums.get("outbox-before-replay.ndjson") != outbox.sha256:
            errors.append("SHA256SUMS does not bind outbox-before-replay.ndjson")

    identities = [mid, final, metadata, lease, replay]
    if any(item.get("task_id") != task_id for item in identities):
        errors.append("one or more evidence files have a mismatched task_id")
    if any(item.get("run_id") != run_id for item in (mid, final, metadata, replay)):
        errors.append("one or more evidence files have a mismatched run_id")

    mid_current = mid.get("current")
    final_current = final.get("current")
    final_total = final.get("total")
    if not _nonnegative_number(mid_current) or not _nonnegative_number(final_total):
        errors.append("checkpoint progress values must be non-negative numbers")
    elif not (0 < mid_current < final_total):
        errors.append("midrun checkpoint must be strictly between zero and final total")
    if final_current != final_total or final_total != manifest.get("total"):
        errors.append("final checkpoint must equal the registered manifest total")

    if not isinstance(metadata.get("command"), list) or not metadata.get("command"):
        errors.append("run_metadata command must be a non-empty list")
    if not isinstance(metadata.get("pid"), int) or metadata.get("pid", 0) <= 0:
        errors.append("run_metadata pid must be positive")
    if lease.get("resource") != "ops-e2e" or lease.get("project") != "uncertainty":
        errors.append("lease evidence must identify uncertainty/ops-e2e")
    if not lease.get("lease_id"):
        errors.append("lease evidence has no lease_id")

    if replay.get("status") != "completed" or replay.get("outbox_drained") is not True:
        errors.append("replay_report must record a completed, drained replay")
    if outbox is not None and replay.get("event_count") != len(outbox.events):
        errors.append("replay event_count does not match archived outbox")

    for field in ("wall_seconds", "worker_hours", "cpu_core_hours", "estimated_cost_cny"):
        if not _nonnegative_number(resources.get(field)):
            errors.append(f"resource_report {field} must be non-negative")
    if resources.get("failure_count") != 0:
        errors.append("resource_report failure_count must be zero")

    log = (directory / "runner.log").read_text(encoding="utf-8", errors="replace")
    for marker in ("lease-acquired", "PROGRESS", "lease-released"):
        if marker not in log:
            errors.append(f"runner.log is missing {marker!r}")

    return {
        "schema_version": 1,
        "status": "accepted" if not errors else "not_accepted",
        "task_id": task_id,
        "run_id": run_id,
        "checks": 8,
        "scientific_gate_credit": 0,
        "errors": errors,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = validate_bundle(args.artifact_dir)
    rendered = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    sys.stdout.write(rendered)
    return 0 if report["status"] == "accepted" else 1


if __name__ == "__main__":
    raise SystemExit(main())
