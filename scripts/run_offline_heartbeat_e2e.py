#!/usr/bin/env python3
"""Run the frozen offline heartbeat/lease E2E protocol on one worker.

This runner never contacts the research-ops control plane.  It forces the
heartbeat wrapper to use the frozen, deliberately unreachable loopback
endpoint and leaves the durable outbox for the separate reviewed replay tool.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import resource
import shutil
import signal
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import yaml

try:
    from scripts.replay_heartbeat_outbox import ReplayError, ValidatedOutbox, validate_outbox
except ImportError:  # direct script execution
    from replay_heartbeat_outbox import ReplayError, ValidatedOutbox, validate_outbox

FROZEN_ENDPOINT = "http://127.0.0.1:1"
FROZEN_TASK_ID = "EXEC-HEARTBEAT-OFFLINE-E2E-v1"
FROZEN_RESOURCE = "ops-e2e"
FROZEN_PROJECT = "uncertainty"
CHECKSUM_NAME = "SHA256SUMS"


class OfflineE2EError(RuntimeError):
    """The frozen E2E protocol could not be executed safely."""


@dataclass(frozen=True)
class Protocol:
    test_id: str
    task_id: str
    endpoint: str
    resource: str
    steps: int
    sleep_seconds: float
    heartbeat_interval_seconds: float


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)


def atomic_copy(source: Path, destination: Path) -> None:
    temporary = destination.with_name(f".{destination.name}.tmp")
    shutil.copyfile(source, temporary)
    os.chmod(temporary, 0o600)
    os.replace(temporary, destination)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_checksums(directory: Path) -> None:
    files = sorted(
        path
        for path in directory.iterdir()
        if path.is_file() and not path.is_symlink() and path.name != CHECKSUM_NAME
    )
    content = "".join(f"{sha256_file(path)}  {path.name}\n" for path in files)
    temporary = directory / f".{CHECKSUM_NAME}.tmp"
    temporary.write_text(content, encoding="utf-8")
    os.chmod(temporary, 0o600)
    os.replace(temporary, directory / CHECKSUM_NAME)


def load_protocol(path: Path) -> Protocol:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise OfflineE2EError(f"cannot load protocol {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise OfflineE2EError("protocol must be a YAML mapping")
    required_exact = {
        "schema_version": 1,
        "test_id": "OFFLINE-HEARTBEAT-E2E-v1",
        "status": "protocol_frozen_execution_pending",
        "task_id": FROZEN_TASK_ID,
        "phase": "EXEC",
        "resource": FROZEN_RESOURCE,
        "endpoint_during_run": FROZEN_ENDPOINT,
        "state_root_rule": "dedicated_persistent_run_directory",
        "replay_mode": "dry_run_then_explicit_apply",
    }
    mismatches = [
        f"{key}={raw.get(key)!r} (expected {expected!r})"
        for key, expected in required_exact.items()
        if raw.get(key) != expected
    ]
    if mismatches:
        raise OfflineE2EError("protocol identity/safety mismatch: " + "; ".join(mismatches))
    try:
        steps = int(raw["steps"])
        sleep_seconds = float(raw["sleep_seconds"])
        interval = float(raw["heartbeat_interval_seconds"])
    except (KeyError, TypeError, ValueError) as exc:
        raise OfflineE2EError("protocol timing fields are invalid") from exc
    if steps != 8 or sleep_seconds <= 0 or interval < 5:
        raise OfflineE2EError(
            "protocol requires 8 steps, positive sleep, and interval >= 5 seconds"
        )
    boundary = raw.get("scientific_boundary")
    if not isinstance(boundary, str) or "must not change science-gate" not in boundary:
        raise OfflineE2EError("protocol does not preserve the science-gate boundary")
    return Protocol(
        test_id=str(raw["test_id"]),
        task_id=str(raw["task_id"]),
        endpoint=str(raw["endpoint_during_run"]),
        resource=str(raw["resource"]),
        steps=steps,
        sleep_seconds=sleep_seconds,
        heartbeat_interval_seconds=interval,
    )


def assert_endpoint_unreachable(endpoint: str, *, timeout: float = 0.25) -> None:
    if endpoint != FROZEN_ENDPOINT:
        raise OfflineE2EError(f"refusing non-frozen endpoint: {endpoint}")
    parsed = urlsplit(endpoint)
    if parsed.scheme != "http" or parsed.hostname != "127.0.0.1" or parsed.port != 1:
        raise OfflineE2EError("offline endpoint must be the frozen loopback TCP port 1")
    try:
        connection = socket.create_connection((parsed.hostname, parsed.port), timeout=timeout)
    except OSError:
        return
    connection.close()
    raise OfflineE2EError(f"offline endpoint is unexpectedly reachable: {endpoint}")


def require_new_output_directory(path: Path) -> Path:
    if path.is_symlink() or path.exists():
        raise OfflineE2EError(f"output directory must not already exist: {path}")
    path.mkdir(parents=True, mode=0o700)
    os.chmod(path, 0o700)
    return path.resolve()


def select_single_file(directory: Path, pattern: str, description: str) -> Path:
    matches = sorted(
        path for path in directory.glob(pattern) if path.is_file() and not path.is_symlink()
    )
    if len(matches) != 1:
        raise OfflineE2EError(
            f"expected exactly one {description} in {directory}, found {len(matches)}"
        )
    return matches[0]


def build_worker_command(
    protocol: Protocol,
    *,
    repository_root: Path,
    lock_root: Path,
) -> list[str]:
    del lock_root  # supplied through the environment; retained here as an explicit contract input
    return [
        str(repository_root / "scripts" / "with_resource_lease.sh"),
        "--resource",
        protocol.resource,
        "--project",
        FROZEN_PROJECT,
        "--task",
        protocol.task_id,
        "--wait",
        "0",
        "--",
        sys.executable,
        str(repository_root / "worker" / "run_with_heartbeat.py"),
        "--task",
        protocol.task_id,
        "--total",
        str(protocol.steps),
        "--unit",
        "checks",
        "--interval",
        str(protocol.heartbeat_interval_seconds),
        "--allow-offline-start",
        "--cwd",
        str(repository_root),
        "--",
        sys.executable,
        "-u",
        str(repository_root / "scripts" / "ops_demo_job.py"),
        "--steps",
        str(protocol.steps),
        "--sleep",
        str(protocol.sleep_seconds),
    ]


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise OfflineE2EError(f"invalid JSON evidence {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise OfflineE2EError(f"evidence must contain a JSON object: {path}")
    return value


def wait_for_midrun_evidence(
    process: subprocess.Popen[bytes],
    *,
    protocol: Protocol,
    state_root: Path,
    lease_path: Path,
    deadline: float,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    while time.monotonic() < deadline:
        checkpoint_files = list((state_root / "checkpoints").glob("*.json"))
        metadata_files = list((state_root / "runs").glob("*.json"))
        if len(checkpoint_files) == 1 and len(metadata_files) == 1 and lease_path.is_file():
            checkpoint = read_json(checkpoint_files[0])
            metadata = read_json(metadata_files[0])
            lease = read_json(lease_path)
            current = checkpoint.get("current")
            if (
                isinstance(current, (int, float))
                and not isinstance(current, bool)
                and 0 < current < protocol.steps
            ):
                return checkpoint, metadata, lease
        if process.poll() is not None:
            raise OfflineE2EError(
                f"worker exited before midrun evidence was captured (exit {process.returncode})"
            )
        time.sleep(0.1)
    raise OfflineE2EError("timed out waiting for an atomic midrun checkpoint")


def validate_finished_outbox(
    outbox_path: Path,
    *,
    task_id: str,
    run_id: str,
    total: int,
) -> ValidatedOutbox:
    try:
        validated = validate_outbox(outbox_path)
    except ReplayError as exc:
        raise OfflineE2EError(f"unsafe offline outbox: {exc}") from exc
    if validated.task_id != task_id or validated.run_id != run_id:
        raise OfflineE2EError("outbox task/run identity differs from captured run metadata")
    currents: list[float] = []
    for event in validated.events:
        current = event.get("current")
        if isinstance(current, (int, float)) and not isinstance(current, bool):
            currents.append(float(current))
    if currents != sorted(currents):
        raise OfflineE2EError("outbox progress is not monotone")
    terminal = validated.events[-1]
    if terminal.get("event") != "done" or terminal.get("current") != total:
        raise OfflineE2EError("outbox does not end in the frozen 8/8 done event")
    metrics = terminal.get("metrics")
    if not isinstance(metrics, dict) or metrics.get("demo_fraction") != 1.0:
        raise OfflineE2EError("terminal outbox event does not contain demo_fraction=1")
    return validated


def verify_release_and_reacquire(
    *,
    command: list[str],
    environment: dict[str, str],
    lease_path: Path,
    log_path: Path,
    deadline_seconds: float = 2.0,
) -> dict[str, Any]:
    released_started = time.monotonic()
    while lease_path.exists() and time.monotonic() - released_started < deadline_seconds:
        time.sleep(0.02)
    release_seconds = time.monotonic() - released_started
    if lease_path.exists() or release_seconds > deadline_seconds:
        raise OfflineE2EError("ops-e2e lease was not released within 2 seconds")

    reacquire = [*command[: command.index("--") + 1], "/usr/bin/true"]
    reacquire_started = time.monotonic()
    try:
        result = subprocess.run(
            reacquire,
            env=environment,
            cwd=environment["OFFLINE_E2E_REPOSITORY_ROOT"],
            capture_output=True,
            text=True,
            timeout=deadline_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise OfflineE2EError("ops-e2e lease could not be reacquired within 2 seconds") from exc
    reacquire_seconds = time.monotonic() - reacquire_started
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write("\n[offline-e2e] lease reacquire probe\n")
        handle.write(result.stdout)
        handle.write(result.stderr)
    if result.returncode != 0 or "lease-acquired" not in result.stdout:
        raise OfflineE2EError(f"ops-e2e lease reacquire probe failed (exit {result.returncode})")
    return {
        "release_detected_seconds": release_seconds,
        "reacquire_seconds": reacquire_seconds,
        "deadline_seconds": deadline_seconds,
        "reacquired": True,
    }


def git_revision(repository_root: Path) -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repository_root,
        capture_output=True,
        text=True,
        check=False,
    )
    revision = result.stdout.strip()
    return revision if result.returncode == 0 and revision else None


def terminate_process(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=5)
    except (ProcessLookupError, subprocess.TimeoutExpired):
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait(timeout=5)


def execute(args: argparse.Namespace) -> Path:
    repository_root = args.repository_root.resolve()
    protocol_path = args.config.resolve()
    protocol = load_protocol(protocol_path)
    assert_endpoint_unreachable(protocol.endpoint)
    output_dir = require_new_output_directory(args.output_dir)
    state_root = output_dir / "state"
    for child in (state_root / "outbox", state_root / "checkpoints", state_root / "runs"):
        child.mkdir(parents=True, mode=0o700)
    lock_root = args.lock_root.resolve()
    lock_root.mkdir(parents=True, exist_ok=True)
    lease_path = lock_root / f"{protocol.resource}.json"
    command = build_worker_command(protocol, repository_root=repository_root, lock_root=lock_root)
    environment = os.environ.copy()
    # The test must fail on loopback directly. AutoDL commonly exports a
    # host-scoped HTTP/SOCKS proxy for userspace Tailscale; inheriting it here
    # could turn a local offline test into an external network request.
    for key in (
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "http_proxy",
        "https_proxy",
        "ALL_PROXY",
        "all_proxy",
    ):
        environment.pop(key, None)
    environment.update(
        {
            "RESEARCH_OPS_ENDPOINT": protocol.endpoint,
            "RESEARCH_OPS_TOKEN": "",
            "RESEARCH_OPS_OWNER": socket.gethostname(),
            "RESEARCH_OPS_STATE_DIR": str(state_root),
            "RESEARCH_OPS_OUTBOX": str(state_root / "outbox"),
            "RESEARCH_OPS_CHECKPOINT_DIR": str(state_root / "checkpoints"),
            "RESEARCH_OPS_RUN_DIR": str(state_root / "runs"),
            "RESEARCH_WORKER_LOCK_ROOT": str(lock_root),
            "OFFLINE_E2E_REPOSITORY_ROOT": str(repository_root),
            "NO_PROXY": "127.0.0.1,localhost",
            "no_proxy": "127.0.0.1,localhost",
        }
    )
    log_path = output_dir / "runner.log"
    started_at = utc_now()
    started_wall = time.monotonic()
    started_usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    process: subprocess.Popen[bytes] | None = None
    try:
        with log_path.open("wb") as log:
            process = subprocess.Popen(
                command,
                cwd=repository_root,
                env=environment,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            mid, metadata, lease = wait_for_midrun_evidence(
                process,
                protocol=protocol,
                state_root=state_root,
                lease_path=lease_path,
                deadline=time.monotonic()
                + max(30.0, protocol.steps * protocol.sleep_seconds + 10.0),
            )
            run_id = metadata.get("run_id")
            if not isinstance(run_id, str) or not run_id:
                raise OfflineE2EError("run metadata has no run_id")
            if mid.get("task_id") != protocol.task_id or mid.get("run_id") != run_id:
                raise OfflineE2EError("midrun checkpoint identity differs from run metadata")
            if lease.get("task") != protocol.task_id:
                raise OfflineE2EError("host lease metadata has the wrong task identity")
            mid_evidence = {**mid, "captured_at": utc_now()}
            lease_evidence = {
                **lease,
                "task_id": protocol.task_id,
                "run_id": run_id,
                "captured_at": utc_now(),
            }
            atomic_json(output_dir / "checkpoint-midrun.json", mid_evidence)
            atomic_json(output_dir / "lease-midrun.json", lease_evidence)
            exit_code = process.wait(
                timeout=max(30.0, protocol.steps * protocol.sleep_seconds + 30.0)
            )
        if exit_code != 0:
            raise OfflineE2EError(f"offline heartbeat demo exited with {exit_code}")

        release = verify_release_and_reacquire(
            command=command,
            environment=environment,
            lease_path=lease_path,
            log_path=log_path,
        )
        checkpoint_path = select_single_file(
            state_root / "checkpoints", "*.json", "final checkpoint"
        )
        metadata_path = select_single_file(state_root / "runs", "*.json", "run metadata")
        outbox_path = select_single_file(state_root / "outbox", "*.ndjson", "heartbeat outbox")
        final = read_json(checkpoint_path)
        final_metadata = read_json(metadata_path)
        run_id = str(final_metadata.get("run_id", ""))
        if (
            final.get("task_id") != protocol.task_id
            or final.get("run_id") != run_id
            or final.get("current") != protocol.steps
            or final.get("total") != protocol.steps
        ):
            raise OfflineE2EError("final checkpoint is not the exact frozen 8/8 run")
        validated = validate_finished_outbox(
            outbox_path,
            task_id=protocol.task_id,
            run_id=run_id,
            total=protocol.steps,
        )
        atomic_json(output_dir / "checkpoint-final.json", final)
        atomic_json(output_dir / "run_metadata.json", final_metadata)
        atomic_copy(outbox_path, output_dir / "outbox-before-replay.ndjson")

        ended_usage = resource.getrusage(resource.RUSAGE_CHILDREN)
        wall_seconds = time.monotonic() - started_wall
        cpu_seconds = (ended_usage.ru_utime + ended_usage.ru_stime) - (
            started_usage.ru_utime + started_usage.ru_stime
        )
        protocol_hash = sha256_file(protocol_path)
        atomic_json(
            output_dir / "run_manifest.json",
            {
                "schema_version": 1,
                "test_id": protocol.test_id,
                "task_id": protocol.task_id,
                "run_id": run_id,
                "phase": "EXEC",
                "status": "ready_for_dry_run_and_controlled_replay",
                "scientific_gate_credit": 0,
                "total": protocol.steps,
                "unit": "checks",
                "endpoint_during_run": protocol.endpoint,
                "endpoint_confirmed_unreachable": True,
                "outbox_event_count": len(validated.events),
                "outbox_sha256": validated.sha256,
                "lease_release_reacquire": release,
                "protocol": str(protocol_path),
                "protocol_sha256": protocol_hash,
                "repository_commit": git_revision(repository_root),
                "started_at": started_at,
                "completed_at": utc_now(),
            },
        )
        atomic_json(
            output_dir / "resource_report.json",
            {
                "schema_version": 1,
                "task_id": protocol.task_id,
                "run_id": run_id,
                "hostname": socket.gethostname(),
                "wall_seconds": wall_seconds,
                "worker_hours": wall_seconds / 3600.0,
                "cpu_core_hours": max(0.0, cpu_seconds) / 3600.0,
                "hourly_price_cny": args.hourly_price_cny,
                "estimated_cost_cny": wall_seconds / 3600.0 * args.hourly_price_cny,
                "failure_count": 0,
            },
        )
        write_checksums(output_dir)
        return output_dir
    except Exception:
        if process is not None:
            terminate_process(process)
        raise


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    repository_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=repository_root / "configs" / "ops" / "offline_heartbeat_e2e_v1.yaml",
    )
    parser.add_argument("--repository-root", type=Path, default=repository_root)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--hourly-price-cny", type=float, default=0.0)
    parser.add_argument(
        "--lock-root",
        type=Path,
        default=Path(os.environ.get("RESEARCH_WORKER_LOCK_ROOT", "/var/lock/research-workers")),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.hourly_price_cny < 0:
        print(
            json.dumps({"status": "failed", "error": "hourly price cannot be negative"}),
            file=sys.stderr,
        )
        return 2
    try:
        output_dir = execute(args)
    except (OfflineE2EError, OSError, subprocess.SubprocessError) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}), file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "status": "ready_for_dry_run_and_controlled_replay",
                "artifact_dir": str(output_dir),
                "scientific_gate_credit": 0,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
