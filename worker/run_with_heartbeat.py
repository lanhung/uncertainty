#!/usr/bin/env python3
"""Run a long job with durable progress heartbeats.

The wrapped command should print absolute progress lines such as
``PROGRESS 420/10000`` and optional metrics such as
``METRIC r_hat=1.008``.  Network failures are buffered locally; permanent API
errors (bad token, unknown task, incomplete dependencies) stop the job before
expensive work begins.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any

ENDPOINT = os.environ.get("RESEARCH_OPS_ENDPOINT", "http://127.0.0.1:8787").rstrip("/")
TOKEN = os.environ.get("RESEARCH_OPS_TOKEN", "")
OWNER = os.environ.get("RESEARCH_OPS_OWNER") or socket.gethostname()
STATE_DIR = Path(os.environ.get("RESEARCH_OPS_STATE_DIR", "state"))
OUTBOX_DIR = Path(os.environ.get("RESEARCH_OPS_OUTBOX", STATE_DIR / "outbox"))
CHECKPOINT_DIR = Path(os.environ.get("RESEARCH_OPS_CHECKPOINT_DIR", STATE_DIR / "checkpoints"))
RUN_DIR = Path(os.environ.get("RESEARCH_OPS_RUN_DIR", STATE_DIR / "runs"))
DEFAULT_PROGRESS_RE = r"\bPROGRESS\s+(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)\b"


class PermanentTransportError(RuntimeError):
    """The server rejected the request; retrying will not help."""


class TransientTransportError(RuntimeError):
    """The control plane could not be reached for the initial start event."""


class Heartbeat:
    def __init__(
        self,
        task_id: str,
        total: float | None,
        unit: str | None,
        interval: float,
        regex: str,
        resume: bool,
        allow_progress_reset: bool,
    ):
        self.task_id = task_id
        self.total = total
        self.unit = unit
        self.interval = interval
        self.pattern = re.compile(regex)
        self.current = 0.0
        self.last_line = ""
        self.metrics: dict[str, float] = {}
        self.run_id = str(uuid.uuid4())
        self._data_lock = threading.Lock()
        self._transport_lock = threading.Lock()
        self._stop = threading.Event()
        self._report_thread: threading.Thread | None = None
        self._interrupted = False
        self.allow_progress_reset = allow_progress_reset

        OUTBOX_DIR.mkdir(parents=True, exist_ok=True)
        CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
        RUN_DIR.mkdir(parents=True, exist_ok=True)
        self.outbox_file = OUTBOX_DIR / f"{task_id}-{self.run_id}.ndjson"
        if resume:
            self._load_checkpoint()

    def _checkpoint_path(self) -> Path:
        return CHECKPOINT_DIR / f"{self.task_id}.json"

    def _load_checkpoint(self) -> None:
        path = self._checkpoint_path()
        if not path.exists():
            return
        try:
            checkpoint = json.loads(path.read_text(encoding="utf-8"))
            self.current = float(checkpoint.get("current", 0))
            if self.total is None and checkpoint.get("total") is not None:
                self.total = float(checkpoint["total"])
            sys.stderr.write(
                f"[heartbeat] resumed task progress at {self.current:g}"
                f"/{self.total if self.total is not None else '?'}\n"
            )
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            sys.stderr.write(f"[heartbeat] ignored invalid checkpoint: {exc}\n")

    @staticmethod
    def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
        temporary = path.with_name(path.name + ".tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, path)

    def save_checkpoint(self) -> None:
        with self._data_lock:
            payload = {
                "task_id": self.task_id,
                "run_id": self.run_id,
                "current": self.current,
                "total": self.total,
                "updated_at_unix": time.time(),
            }
        self._atomic_json(self._checkpoint_path(), payload)

    def write_run_metadata(self, command: list[str], pid: int | None = None) -> None:
        self._atomic_json(
            RUN_DIR / f"{self.task_id}-{self.run_id}.json",
            {
                "task_id": self.task_id,
                "run_id": self.run_id,
                "owner": OWNER,
                "endpoint": ENDPOINT,
                "command": command,
                "pid": pid,
                "started_at_unix": time.time(),
            },
        )

    def _request(self, body: dict[str, Any]) -> str:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            f"{ENDPOINT}/report",
            data=data,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        if TOKEN:
            request.add_header("Authorization", f"Bearer {TOKEN}")
        try:
            with urllib.request.urlopen(request, timeout=8) as response:
                response.read()
            return "ok"
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            if 400 <= exc.code < 500:
                raise PermanentTransportError(
                    f"server rejected heartbeat ({exc.code}): {detail}"
                ) from exc
            return "retry"
        except (urllib.error.URLError, TimeoutError):
            return "retry"

    def _buffer(self, body: dict[str, Any]) -> None:
        with open(self.outbox_file, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(body, ensure_ascii=False) + "\n")

    def _drain_locked(self) -> bool:
        if not self.outbox_file.exists():
            return True
        try:
            lines = self.outbox_file.read_text(encoding="utf-8").splitlines()
        except OSError:
            return False
        remaining: list[str] = []
        transport_available = True
        for index, line in enumerate(lines):
            if not line.strip():
                continue
            try:
                body = json.loads(line)
                result = self._request(body)
                if result == "retry":
                    remaining.append(line)
                    remaining.extend(item for item in lines[index + 1 :] if item.strip())
                    transport_available = False
                    break
            except PermanentTransportError as exc:
                sys.stderr.write(f"[heartbeat] dropping permanently rejected event: {exc}\n")
            except (json.JSONDecodeError, TypeError) as exc:
                sys.stderr.write(f"[heartbeat] dropping corrupt outbox event: {exc}\n")
        if remaining:
            self.outbox_file.write_text("\n".join(remaining) + "\n", encoding="utf-8")
        else:
            self.outbox_file.unlink(missing_ok=True)
        return transport_available

    def send(self, body: dict[str, Any], *, strict: bool = False) -> bool:
        body.setdefault("event_id", str(uuid.uuid4()))
        body.setdefault("run_id", self.run_id)
        with self._transport_lock:
            if not self._drain_locked():
                self._buffer(body)
                if strict:
                    raise TransientTransportError(
                        f"control plane unavailable at {ENDPOINT}; start event buffered"
                    )
                return False
            try:
                result = self._request(body)
            except PermanentTransportError:
                if strict:
                    raise
                sys.stderr.write("[heartbeat] permanent server rejection; event not buffered\n")
                return False
            if result == "ok":
                return True
            self._buffer(body)
            if strict:
                raise TransientTransportError(
                    f"control plane unavailable at {ENDPOINT}; start event buffered"
                )
            return False

    def observe(self, line: str) -> None:
        with self._data_lock:
            self.last_line = line.strip()[:500]
            match = self.pattern.search(line)
            if match:
                try:
                    parsed = float(match.group(1))
                    if self.allow_progress_reset:
                        self.current = parsed
                    else:
                        self.current = max(self.current, parsed)
                    if match.lastindex and match.lastindex >= 2 and self.total is None:
                        self.total = float(match.group(2))
                except (ValueError, IndexError):
                    pass
            for metric in re.finditer(
                r"\bMETRIC\s+([A-Za-z0-9_.-]+)=([-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)",
                line,
            ):
                try:
                    self.metrics[metric.group(1)] = float(metric.group(2))
                except ValueError:
                    pass

    def _body(self, event: str, **extra: Any) -> dict[str, Any]:
        with self._data_lock:
            body: dict[str, Any] = {
                "task_id": self.task_id,
                "event": event,
                "run_id": self.run_id,
                "owner": OWNER,
                "current": self.current,
                "total": self.total,
                "unit": self.unit,
                "message": self.last_line,
            }
            if self.metrics:
                body["metrics"] = dict(self.metrics)
        body.update(extra)
        return body

    def start_reporting(
        self,
        *,
        allow_offline_start: bool = False,
        force_start: bool = False,
    ) -> None:
        self.send(
            {
                "task_id": self.task_id,
                "event": "start",
                "run_id": self.run_id,
                "owner": OWNER,
                "total": self.total,
                "unit": self.unit,
                "force": force_start,
            },
            strict=not allow_offline_start,
        )
        self._report_thread = threading.Thread(
            target=self._loop,
            name=f"heartbeat-{self.task_id}",
            daemon=True,
        )
        self._report_thread.start()

    def _loop(self) -> None:
        while not self._stop.wait(self.interval):
            self.emit("progress")

    def emit(self, event: str, **extra: Any) -> None:
        self.save_checkpoint()
        self.send(self._body(event, **extra))

    def interrupt(self, signum: int) -> None:
        if self._interrupted:
            return
        self._interrupted = True
        self._stop.set()
        self.emit("block", reason=f"interrupted by signal {signum}")

    def finish(self, code: int) -> None:
        self._stop.set()
        if self._report_thread is not None:
            self._report_thread.join(timeout=max(1.0, min(5.0, self.interval)))
        if self._interrupted:
            return
        if code == 0:
            self.emit("done", message=self.last_line or "completed")
        else:
            self.emit("fail", reason=f"exit code {code}: {self.last_line}")


def terminate_process_group(process: subprocess.Popen[str], grace_s: float = 20.0) -> None:
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    deadline = time.time() + grace_s
    while process.poll() is None and time.time() < deadline:
        time.sleep(0.2)
    if process.poll() is None:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", required=True)
    parser.add_argument("--total", type=float)
    parser.add_argument("--unit", default="units")
    parser.add_argument("--interval", type=float, default=30.0)
    parser.add_argument("--progress-regex", default=DEFAULT_PROGRESS_RE)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--allow-progress-reset", action="store_true")
    parser.add_argument(
        "--allow-offline-start",
        action="store_true",
        help="start even when the control plane is initially unreachable",
    )
    parser.add_argument(
        "--force-start",
        action="store_true",
        help="start despite incomplete plan dependencies; reserved for approved diagnostics",
    )
    parser.add_argument("--cwd")
    parser.add_argument(
        "cmd",
        nargs=argparse.REMAINDER,
        help="command following --",
    )
    args = parser.parse_args()

    command = args.cmd[1:] if args.cmd and args.cmd[0] == "--" else args.cmd
    if not command:
        parser.error("no command supplied after --")
    if args.interval < 5:
        parser.error("--interval must be at least 5 seconds")

    heartbeat = Heartbeat(
        args.task,
        args.total,
        args.unit,
        args.interval,
        args.progress_regex,
        args.resume,
        args.allow_progress_reset,
    )
    heartbeat.write_run_metadata(command)
    try:
        heartbeat.start_reporting(
            allow_offline_start=args.allow_offline_start,
            force_start=args.force_start,
        )
    except (PermanentTransportError, TransientTransportError) as exc:
        sys.stderr.write(f"run_with_heartbeat: refusing to start expensive job: {exc}\n")
        raise SystemExit(78) from exc

    child_env = os.environ.copy()
    child_env.setdefault("PYTHONUNBUFFERED", "1")
    try:
        process = subprocess.Popen(
            command,
            cwd=args.cwd,
            env=child_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            start_new_session=True,
        )
    except OSError as exc:
        heartbeat.emit("fail", reason=f"failed to launch command: {exc}")
        raise SystemExit(127) from exc
    heartbeat.write_run_metadata(command, process.pid)

    def handle_signal(signum: int, _frame: Any) -> None:
        heartbeat.interrupt(signum)
        terminate_process_group(process)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    assert process.stdout is not None
    for line in process.stdout:
        sys.stdout.write(line)
        sys.stdout.flush()
        heartbeat.observe(line)
    code = process.wait()
    heartbeat.finish(code)
    raise SystemExit(code)


if __name__ == "__main__":
    main()
