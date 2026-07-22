#!/usr/bin/env python3
"""Small stdlib-only CLI for the research operations status server."""

from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import urllib.error
import urllib.request
import uuid
from typing import Any

ENDPOINT = os.environ.get("RESEARCH_OPS_ENDPOINT", "http://127.0.0.1:8787").rstrip("/")
TOKEN = os.environ.get("RESEARCH_OPS_TOKEN", "")
OWNER = os.environ.get("RESEARCH_OPS_OWNER") or socket.gethostname()


def _call(method: str, path: str, body: dict[str, Any] | None = None) -> Any:
    url = f"{ENDPOINT}{path}"
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    if TOKEN:
        request.add_header("Authorization", f"Bearer {TOKEN}")
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            raw = response.read().decode("utf-8")
            content_type = response.headers.get("Content-Type", "")
            if "json" in content_type:
                return json.loads(raw)
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return raw
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1000]
        sys.stderr.write(f"taskctl: server returned {exc.code}: {detail}\n")
        raise SystemExit(2) from exc
    except urllib.error.URLError as exc:
        sys.stderr.write(f"taskctl: cannot reach {ENDPOINT}: {exc.reason}\n")
        raise SystemExit(3) from exc


def _metrics(pairs: list[str] | None) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for pair in pairs or []:
        if "=" not in pair:
            raise SystemExit(f"invalid metric {pair!r}; expected key=value")
        key, value = pair.split("=", 1)
        if not key:
            raise SystemExit("metric key may not be empty")
        try:
            output[key] = float(value)
        except ValueError:
            if value.lower() in {"true", "false"}:
                output[key] = value.lower() == "true"
            else:
                output[key] = value
    return output


def _report(event: str, task_id: str, **kwargs: Any) -> None:
    body: dict[str, Any] = {
        "task_id": task_id,
        "event": event,
        "event_id": str(uuid.uuid4()),
        "owner": OWNER,
    }
    body.update({key: value for key, value in kwargs.items() if value is not None})
    print(json.dumps(_call("POST", "/report", body), indent=2, ensure_ascii=False))


def _age(seconds: float | None) -> str:
    if seconds is None:
        return "—"
    if seconds < 60:
        return f"{seconds:.0f}s"
    if seconds < 3600:
        return f"{seconds / 60:.0f}m"
    return f"{seconds / 3600:.1f}h"


def show(*, json_output: bool = False) -> None:
    snapshot = _call("GET", "/api/state")
    if json_output:
        print(json.dumps(snapshot, indent=2, ensure_ascii=False))
        return
    science = 100 * snapshot.get("science_gate_progress", snapshot.get("overall_progress", 0))
    execution = 100 * snapshot.get("execution_progress", 0)
    print(
        f"\n  {snapshot.get('project', '')}  science gate {science:.0f}%  "
        f"execution {execution:.0f}%  "
        f"rev {snapshot.get('revision', 0)}"
    )
    counts = snapshot.get("status_counts", {})
    if counts:
        print("  " + "  ".join(f"{key}:{value}" for key, value in counts.items()))
    print()

    current_phase = None
    for task in snapshot.get("tasks", []):
        phase = task.get("phase") or "misc"
        if phase != current_phase:
            print(f"  [{phase}]")
            current_phase = phase
        percentage = 100 * task.get("progress", 0)
        bar_size = max(0, min(20, int(percentage / 5)))
        bar = "#" * bar_size + "." * (20 - bar_size)
        total = task.get("total")
        counter = (
            f"{task.get('current', 0):g}/{total:g} {task.get('unit', '')}"
            if total is not None
            else "—"
        )
        ready = " READY" if task.get("ready") else ""
        print(
            f"    {task['id']:<28} {task['status']:<9} [{bar}] {percentage:5.1f}%  {counter}{ready}"
        )
        if task.get("owner"):
            print(
                f"        owner {task['owner']}  attempt {task.get('attempt', 0)}  "
                f"heartbeat {_age(task.get('heartbeat_age_s'))}"
            )
        if task.get("blocked_by"):
            print(f"        blocked by: {', '.join(task['blocked_by'])}")
        if task.get("eta"):
            print(f"        eta {task['eta']} ({task.get('eta_kind', 'none')})")
        if task.get("metrics"):
            print(
                "        metrics "
                + ", ".join(f"{key}={value}" for key, value in task["metrics"].items())
            )
        if task.get("message"):
            print(f"        · {task['message']}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(prog="taskctl")
    subparsers = parser.add_subparsers(dest="command", required=True)

    def task_parser(name: str) -> argparse.ArgumentParser:
        child = subparsers.add_parser(name)
        child.add_argument("task_id")
        return child

    child = task_parser("start")
    child.add_argument("--total", type=float)
    child.add_argument("--unit")
    child.add_argument("--force", action="store_true")

    child = task_parser("progress")
    child.add_argument("--current", type=float, required=True)
    child.add_argument("--total", type=float)
    child.add_argument("--message")
    child.add_argument("--metric", action="append")

    child = task_parser("done")
    child.add_argument("--message")
    child.add_argument("--metric", action="append")

    child = task_parser("fail")
    child.add_argument("--reason", required=True)

    child = task_parser("block")
    child.add_argument("--reason", required=True)

    child = task_parser("cancel")
    child.add_argument("--reason", required=True)

    child = task_parser("note")
    child.add_argument("message")

    child = task_parser("artifact")
    child.add_argument("path")

    subparsers.add_parser("reconcile")
    subparsers.add_parser("snapshot")
    subparsers.add_parser("health")
    subparsers.add_parser("summary")
    child = subparsers.add_parser("show")
    child.add_argument("--json", action="store_true")

    args = parser.parse_args()
    command = args.command
    if command == "start":
        _report(
            "start",
            args.task_id,
            total=args.total,
            unit=args.unit,
            force=args.force,
        )
    elif command == "progress":
        _report(
            "progress",
            args.task_id,
            current=args.current,
            total=args.total,
            message=args.message,
            metrics=_metrics(args.metric) or None,
        )
    elif command == "done":
        _report(
            "done",
            args.task_id,
            message=args.message,
            metrics=_metrics(args.metric) or None,
        )
    elif command == "fail":
        _report("fail", args.task_id, reason=args.reason)
    elif command == "block":
        _report("block", args.task_id, reason=args.reason)
    elif command == "cancel":
        _report("cancel", args.task_id, reason=args.reason)
    elif command == "note":
        _report("note", args.task_id, message=args.message)
    elif command == "artifact":
        _report("artifact", args.task_id, artifact=args.path)
    elif command == "reconcile":
        print(json.dumps(_call("POST", "/reconcile"), indent=2, ensure_ascii=False))
    elif command == "snapshot":
        print(json.dumps(_call("POST", "/snapshot"), indent=2, ensure_ascii=False))
    elif command == "health":
        print(json.dumps(_call("GET", "/healthz"), indent=2, ensure_ascii=False))
    elif command == "summary":
        print(_call("GET", "/api/summary"))
    elif command == "show":
        show(json_output=args.json)


if __name__ == "__main__":
    main()
