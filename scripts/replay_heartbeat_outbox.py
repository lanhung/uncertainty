#!/usr/bin/env python3
"""Validate and safely replay one durable heartbeat outbox.

The bearer token is deliberately accepted only through ``RESEARCH_OPS_TOKEN``.
An apply run archives the complete original outbox before sending any event.
Acknowledged prefixes are then removed atomically; an interrupted replay can be
restarted because every event carries its original idempotency key.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import sys
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import yaml

TERMINAL_EVENTS = {"done", "fail", "block"}
REPLAYABLE_EVENTS = {"start", "progress", *TERMINAL_EVENTS}


class ReplayError(RuntimeError):
    """The outbox is unsafe to replay or a replay attempt could not continue."""


class ReplayTransportError(ReplayError):
    """The endpoint did not durably acknowledge the next event."""


@dataclass(frozen=True)
class ValidatedOutbox:
    path: Path
    raw: bytes
    raw_lines: tuple[bytes, ...]
    events: tuple[dict[str, Any], ...]
    task_id: str
    run_id: str
    sha256: str


def _atomic_write(path: Path, content: bytes, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        temporary.unlink(missing_ok=True)


def _unlink_durable(path: Path) -> None:
    path.unlink(missing_ok=True)
    directory_fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def validate_outbox(path: str | Path) -> ValidatedOutbox:
    outbox = Path(path)
    if outbox.is_symlink() or not outbox.is_file():
        raise ReplayError(f"outbox must be a regular, non-symlink file: {outbox}")
    raw = outbox.read_bytes()
    if not raw:
        raise ReplayError("outbox is empty")
    raw_lines = tuple(raw.splitlines(keepends=True))
    events: list[dict[str, Any]] = []
    for line_number, raw_line in enumerate(raw_lines, start=1):
        if not raw_line.strip():
            raise ReplayError(f"outbox line {line_number} is blank")
        try:
            decoded = raw_line.decode("utf-8")
            event = json.loads(decoded)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ReplayError(f"outbox line {line_number} is not valid UTF-8 JSON: {exc}") from exc
        if not isinstance(event, dict):
            raise ReplayError(f"outbox line {line_number} must contain a JSON object")
        events.append(event)

    task_ids = {event.get("task_id") for event in events}
    run_ids = {event.get("run_id") for event in events}
    if len(task_ids) != 1 or not all(isinstance(value, str) and value for value in task_ids):
        raise ReplayError("all events must have one non-empty task_id")
    if len(run_ids) != 1 or not all(isinstance(value, str) and value for value in run_ids):
        raise ReplayError("all events must have one non-empty run_id")

    event_ids: list[str] = []
    for index, event in enumerate(events):
        kind = event.get("event")
        if kind not in REPLAYABLE_EVENTS:
            raise ReplayError(f"event {index + 1} has unsupported type {kind!r}")
        event_id = event.get("event_id")
        if not isinstance(event_id, str) or not event_id:
            raise ReplayError(f"event {index + 1} has no non-empty event_id")
        event_ids.append(event_id)
    if len(set(event_ids)) != len(event_ids):
        raise ReplayError("event_id values must be unique within the outbox")
    if events[0].get("event") != "start":
        raise ReplayError("the first outbox event must be start")
    if events[-1].get("event") not in TERMINAL_EVENTS:
        raise ReplayError("the last outbox event must be done, fail, or block")
    if any(event.get("event") in TERMINAL_EVENTS for event in events[:-1]):
        raise ReplayError("a terminal event may appear only as the final event")
    if any(event.get("event") == "start" for event in events[1:]):
        raise ReplayError("the start event may appear only once and first")

    return ValidatedOutbox(
        path=outbox,
        raw=raw,
        raw_lines=raw_lines,
        events=tuple(events),
        task_id=next(iter(task_ids)),
        run_id=next(iter(run_ids)),
        sha256=hashlib.sha256(raw).hexdigest(),
    )


def require_exec_task(plan_path: str | Path, task_id: str) -> None:
    plan_file = Path(plan_path)
    try:
        plan = yaml.safe_load(plan_file.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise ReplayError(f"cannot load plan {plan_file}: {exc}") from exc
    tasks = plan.get("tasks") if isinstance(plan, dict) else None
    if not isinstance(tasks, list):
        raise ReplayError(f"plan has no task list: {plan_file}")
    matches = [item for item in tasks if isinstance(item, dict) and item.get("id") == task_id]
    if len(matches) != 1:
        raise ReplayError(f"task {task_id!r} is not uniquely present in {plan_file}")
    if matches[0].get("phase") != "EXEC":
        raise ReplayError(f"refusing replay for non-EXEC task {task_id!r}")


def archive_outbox(validated: ValidatedOutbox, archive_dir: str | Path) -> Path:
    archive_root = Path(archive_dir)
    safe_run = re.sub(r"[^A-Za-z0-9_.-]+", "_", validated.run_id).strip("._") or "run"
    archive = archive_root / f"{validated.path.stem}-{safe_run}-{validated.sha256[:12]}.ndjson"
    if archive.exists():
        if archive.read_bytes() != validated.raw:
            raise ReplayError(f"archive collision with different content: {archive}")
    else:
        _atomic_write(archive, validated.raw)
    digest_file = archive.with_suffix(archive.suffix + ".sha256")
    digest_line = f"{validated.sha256}  {archive.name}\n".encode()
    if digest_file.exists() and digest_file.read_bytes() != digest_line:
        raise ReplayError(f"archive digest collision: {digest_file}")
    if not digest_file.exists():
        _atomic_write(digest_file, digest_line)
    return archive


def _post_event(endpoint: str, token: str, event: dict[str, Any]) -> dict[str, Any]:
    request = urllib.request.Request(
        f"{endpoint.rstrip('/')}/report",
        data=json.dumps(event, ensure_ascii=False).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise ReplayTransportError(f"server returned HTTP {exc.code}: {detail}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ReplayTransportError(f"control plane unavailable: {exc}") from exc
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ReplayTransportError("server returned a non-JSON acknowledgement") from exc
    if not isinstance(payload, dict) or payload.get("ok") is not True:
        raise ReplayTransportError(f"server did not acknowledge event: {payload!r}")
    return payload


def _acknowledge_prefix(path: Path, remaining: tuple[bytes, ...]) -> None:
    if remaining:
        _atomic_write(path, b"".join(remaining))
    else:
        _unlink_durable(path)


def _state_path(outbox: Path) -> Path:
    return outbox.with_name(outbox.name + ".replay-state.json")


def _write_replay_state(path: Path, validated: ValidatedOutbox, archive: Path) -> None:
    payload = {
        "schema_version": 1,
        "task_id": validated.task_id,
        "run_id": validated.run_id,
        "archive": str(archive.resolve()),
        "archive_sha256": validated.sha256,
        "event_count": len(validated.events),
    }
    _atomic_write(path, (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode())


def _resume_session(outbox: Path, state_path: Path) -> tuple[ValidatedOutbox, Path, int]:
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReplayError(f"invalid replay state {state_path}: {exc}") from exc
    if not isinstance(state, dict) or state.get("schema_version") != 1:
        raise ReplayError(f"invalid replay state schema: {state_path}")
    archive_value = state.get("archive")
    if not isinstance(archive_value, str) or not archive_value:
        raise ReplayError("replay state has no archive path")
    archive = Path(archive_value)
    validated = validate_outbox(archive)
    if (
        state.get("task_id") != validated.task_id
        or state.get("run_id") != validated.run_id
        or state.get("archive_sha256") != validated.sha256
        or state.get("event_count") != len(validated.events)
    ):
        raise ReplayError("replay state does not match its immutable archive")
    if not outbox.exists():
        # Only a successful final acknowledgement removes the outbox. State
        # remains until the next operation, so a crash between unlink and
        # state cleanup can finish without resending or losing evidence.
        return validated, archive, len(validated.events)
    if outbox.is_symlink() or not outbox.is_file():
        raise ReplayError(f"partial replay outbox is unsafe: {outbox}")
    remaining_raw = outbox.read_bytes()
    offsets = [
        index
        for index in range(len(validated.raw_lines))
        if b"".join(validated.raw_lines[index:]) == remaining_raw
    ]
    if len(offsets) != 1:
        raise ReplayError("current outbox is not an exact unacknowledged suffix of its archive")
    return validated, archive, offsets[0]


def replay_outbox(
    path: str | Path,
    *,
    plan_path: str | Path,
    endpoint: str,
    token: str,
    archive_dir: str | Path,
    sender: Callable[[str, str, dict[str, Any]], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if not endpoint:
        raise ReplayError("RESEARCH_OPS_ENDPOINT is required for apply")
    if not token:
        raise ReplayError("RESEARCH_OPS_TOKEN is required for apply")
    outbox = Path(path)
    lock_path = outbox.with_name(outbox.name + ".replay.lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with open(lock_path, "a+b") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        state_path = _state_path(outbox)
        if state_path.exists():
            validated, archive, acknowledged = _resume_session(outbox, state_path)
        else:
            validated = validate_outbox(outbox)
            archive = archive_outbox(validated, archive_dir)
            _write_replay_state(state_path, validated, archive)
            acknowledged = 0
        require_exec_task(plan_path, validated.task_id)
        send = sender or _post_event
        remaining = validated.raw_lines[acknowledged:]
        acknowledgements: list[dict[str, Any]] = []
        for event in validated.events[acknowledged:]:
            try:
                acknowledgement = send(endpoint, token, event)
            except Exception as exc:
                if isinstance(exc, ReplayError):
                    raise
                raise ReplayTransportError(f"event was not acknowledged: {exc}") from exc
            if not isinstance(acknowledgement, dict) or acknowledgement.get("ok") is not True:
                raise ReplayTransportError(
                    f"event was not durably acknowledged: {acknowledgement!r}"
                )
            acknowledgements.append(acknowledgement)
            remaining = remaining[1:]
            _acknowledge_prefix(outbox, remaining)
        _unlink_durable(state_path)
        return {
            "status": "completed",
            "task_id": validated.task_id,
            "run_id": validated.run_id,
            "event_count": len(validated.events),
            "events_replayed_this_invocation": len(acknowledgements),
            "duplicate_acknowledgements": sum(
                acknowledgement.get("duplicate") is True for acknowledgement in acknowledgements
            ),
            "archive": str(archive),
            "archive_sha256": validated.sha256,
            "outbox_drained": not outbox.exists(),
        }


def dry_run(path: str | Path, plan_path: str | Path) -> dict[str, Any]:
    validated = validate_outbox(path)
    require_exec_task(plan_path, validated.task_id)
    return {
        "status": "validated",
        "task_id": validated.task_id,
        "run_id": validated.run_id,
        "event_count": len(validated.events),
        "terminal_event": validated.events[-1]["event"],
        "sha256": validated.sha256,
        "outbox_unchanged": True,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    parser.add_argument("--outbox", type=Path, required=True)
    parser.add_argument("--plan", type=Path, default=Path("plan/plan.yaml"))
    parser.add_argument("--archive-dir", type=Path)
    parser.add_argument(
        "--endpoint",
        default=os.environ.get("RESEARCH_OPS_ENDPOINT", ""),
        help="control-plane URL; defaults to RESEARCH_OPS_ENDPOINT",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.dry_run:
            result = dry_run(args.outbox, args.plan)
        else:
            archive_dir = args.archive_dir or args.outbox.parent / "archive"
            result = replay_outbox(
                args.outbox,
                plan_path=args.plan,
                endpoint=args.endpoint,
                token=os.environ.get("RESEARCH_OPS_TOKEN", ""),
                archive_dir=archive_dir,
            )
    except ReplayError as exc:
        print(
            json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False), file=sys.stderr
        )
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
