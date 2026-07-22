"""Thread-safe SQLite task ledger for the research operations control plane.

Only the status server should mutate this store.  Workers and humans interact
through the HTTP API, which keeps one durable source of truth while still
allowing concurrent heartbeat requests inside one FastAPI process.
"""

from __future__ import annotations

import json
import sqlite3
import statistics
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VALID_STATUS = {
    "pending",
    "running",
    "blocked",
    "stale",  # derived on read; normally not persisted
    "done",
    "failed",
    "cancelled",
}
DEFAULT_STALE_AFTER_S = 15 * 60
RATE_WINDOW_S = 10 * 60
EVENT_RETENTION_S = 30 * 24 * 3600
SAMPLE_RETENTION_S = 7 * 24 * 3600


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _parse_iso(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).timestamp()
    except ValueError:
        return None


@dataclass
class Task:
    id: str
    title: str = ""
    phase: str = ""
    status: str = "pending"
    weight: float = 1.0
    unit: str = "units"
    current: float = 0.0
    total: float | None = None
    owner: str | None = None
    depends_on: list[str] = field(default_factory=list)
    started_at: str | None = None
    updated_at: str | None = None
    finished_at: str | None = None
    declared_eta: str | None = None
    message: str = ""
    artifacts: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    attempt: int = 0
    run_id: str | None = None

    # Derived fields; never persisted.
    progress: float = 0.0
    rate: float | None = None
    eta: str | None = None
    eta_kind: str = "none"
    heartbeat_age_s: float | None = None
    ready: bool = False
    blocked_by: list[str] = field(default_factory=list)

    def to_static(self) -> dict[str, Any]:
        data = asdict(self)
        for key in (
            "progress",
            "rate",
            "eta",
            "eta_kind",
            "heartbeat_age_s",
            "ready",
            "blocked_by",
        ):
            data.pop(key, None)
        return data


class Store:
    """Serialized task store backed by SQLite WAL mode."""

    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(
            self.db_path,
            check_same_thread=False,
            timeout=10,
        )
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA synchronous=NORMAL")
            self._conn.execute("PRAGMA busy_timeout=10000")
            self._init_locked()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def _init_locked(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id   TEXT PRIMARY KEY,
                data TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS samples (
                task_id TEXT NOT NULL,
                ts      REAL NOT NULL,
                current REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_samples_task_ts
                ON samples(task_id, ts);
            CREATE TABLE IF NOT EXISTS events (
                event_id TEXT PRIMARY KEY,
                ts       REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS meta (
                k TEXT PRIMARY KEY,
                v TEXT
            );
            """
        )
        self._conn.commit()

    # ---- meta / revisions -------------------------------------------------
    def _set_meta_locked(self, key: str, value: str) -> None:
        self._conn.execute(
            "INSERT INTO meta(k,v) VALUES(?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v",
            (key, value),
        )

    def set_meta(self, key: str, value: str) -> None:
        with self._lock:
            self._set_meta_locked(key, value)
            self._conn.commit()

    def get_meta(self, key: str, default: str = "") -> str:
        with self._lock:
            row = self._conn.execute("SELECT v FROM meta WHERE k=?", (key,)).fetchone()
            return row["v"] if row else default

    def revision(self) -> int:
        try:
            return int(self.get_meta("revision", "0"))
        except ValueError:
            return 0

    def _bump_revision_locked(self) -> int:
        row = self._conn.execute("SELECT v FROM meta WHERE k='revision'").fetchone()
        current = int(row["v"]) if row and str(row["v"]).isdigit() else 0
        current += 1
        self._set_meta_locked("revision", str(current))
        return current

    # ---- idempotency ------------------------------------------------------
    def claim_event(self, event_id: str | None) -> bool:
        """Return False when an event has already been applied."""
        if not event_id:
            return True
        now = time.time()
        with self._lock:
            cur = self._conn.execute(
                "INSERT OR IGNORE INTO events(event_id,ts) VALUES(?,?)",
                (event_id, now),
            )
            self._conn.execute("DELETE FROM events WHERE ts<?", (now - EVENT_RETENTION_S,))
            self._conn.commit()
            return cur.rowcount == 1

    # ---- raw task I/O -----------------------------------------------------
    def _write_locked(self, task: Task, *, bump: bool = True) -> None:
        self._conn.execute(
            "INSERT INTO tasks(id,data) VALUES(?,?) "
            "ON CONFLICT(id) DO UPDATE SET data=excluded.data",
            (task.id, json.dumps(task.to_static(), ensure_ascii=False)),
        )
        if bump:
            self._bump_revision_locked()
        self._conn.commit()

    def get(self, task_id: str) -> Task | None:
        with self._lock:
            row = self._conn.execute("SELECT data FROM tasks WHERE id=?", (task_id,)).fetchone()
            if not row:
                return None
            return Task(**json.loads(row["data"]))

    def all_ids(self) -> list[str]:
        with self._lock:
            return [row["id"] for row in self._conn.execute("SELECT id FROM tasks ORDER BY id")]

    def upsert_static(self, task: Task) -> None:
        with self._lock:
            self._write_locked(task)

    # ---- runtime events ---------------------------------------------------
    @staticmethod
    def _touch(task: Task) -> None:
        task.updated_at = now_iso()

    def start(
        self,
        task_id: str,
        owner: str | None,
        total: float | None,
        unit: str | None,
        run_id: str | None,
    ) -> Task:
        with self._lock:
            task = self.get(task_id) or Task(id=task_id)
            if task.status not in ("running", "stale") or (run_id and task.run_id != run_id):
                task.attempt += 1
            task.status = "running"
            task.owner = owner or task.owner
            task.run_id = run_id or task.run_id
            task.finished_at = None
            if total is not None:
                task.total = float(total)
            if unit:
                task.unit = unit
            if not task.started_at or task.attempt > 1:
                task.started_at = now_iso()
            self._touch(task)
            self._write_locked(task)
            return task

    def _assert_run_locked(self, task: Task, run_id: str | None) -> None:
        if run_id and task.run_id and run_id != task.run_id:
            raise ValueError(f"stale run_id for {task.id}: active={task.run_id}, got={run_id}")

    def progress(
        self,
        task_id: str,
        current: float,
        total: float | None,
        message: str | None,
        metrics: dict[str, Any] | None,
        owner: str | None,
        run_id: str | None,
    ) -> Task:
        with self._lock:
            task = self.get(task_id) or Task(id=task_id)
            self._assert_run_locked(task, run_id)
            if task.status not in ("running", "stale"):
                task.status = "running"
                task.started_at = task.started_at or now_iso()
            task.current = float(current)
            if total is not None:
                task.total = float(total)
            if message is not None:
                task.message = message
            if owner:
                task.owner = owner
            if run_id:
                task.run_id = run_id
            if metrics:
                task.metrics.update(metrics)
            self._touch(task)
            self._write_locked(task)
            now = time.time()
            self._conn.execute(
                "INSERT INTO samples(task_id,ts,current) VALUES(?,?,?)",
                (task_id, now, float(current)),
            )
            self._conn.execute("DELETE FROM samples WHERE ts<?", (now - SAMPLE_RETENTION_S,))
            self._conn.commit()
            return task

    def finish(
        self,
        task_id: str,
        status: str,
        message: str | None,
        metrics: dict[str, Any] | None,
        run_id: str | None,
    ) -> Task:
        if status not in ("done", "failed", "blocked", "cancelled"):
            raise ValueError(f"invalid terminal status: {status}")
        with self._lock:
            task = self.get(task_id) or Task(id=task_id)
            self._assert_run_locked(task, run_id)
            task.status = status
            if message is not None:
                task.message = message
            if metrics:
                task.metrics.update(metrics)
            if status == "done" and task.total is not None:
                task.current = task.total
            task.finished_at = now_iso()
            self._touch(task)
            self._write_locked(task)
            return task

    def note(self, task_id: str, message: str) -> Task:
        with self._lock:
            task = self.get(task_id) or Task(id=task_id)
            task.message = message
            self._touch(task)
            self._write_locked(task)
            return task

    def add_artifact(self, task_id: str, path: str) -> Task:
        with self._lock:
            task = self.get(task_id) or Task(id=task_id)
            if path not in task.artifacts:
                task.artifacts.append(path)
            self._touch(task)
            self._write_locked(task)
            return task

    # ---- ETA / derived fields --------------------------------------------
    def _rate(self, task_id: str) -> float | None:
        cutoff = time.time() - RATE_WINDOW_S
        with self._lock:
            rows = self._conn.execute(
                "SELECT ts,current FROM samples WHERE task_id=? AND ts>=? ORDER BY ts",
                (task_id, cutoff),
            ).fetchall()
        if len(rows) < 2:
            return None
        slopes: list[float] = []
        for left, right in zip(rows, rows[1:]):
            dt = right["ts"] - left["ts"]
            dc = right["current"] - left["current"]
            if dt > 0 and dc > 0:
                slopes.append(dc / dt)
        if not slopes:
            return None
        return statistics.median(slopes)

    def hydrate(self, task: Task, stale_after_s: int) -> Task:
        if task.status == "done":
            task.progress = 1.0
        elif task.status == "cancelled":
            task.progress = 0.0
        elif task.total and task.total > 0:
            task.progress = max(0.0, min(1.0, task.current / task.total))
        else:
            task.progress = 0.0

        last = _parse_iso(task.updated_at)
        if last is not None:
            task.heartbeat_age_s = max(0.0, time.time() - last)
        if (
            task.status == "running"
            and task.heartbeat_age_s is not None
            and task.heartbeat_age_s > stale_after_s
        ):
            task.status = "stale"

        task.rate = None
        task.eta = None
        task.eta_kind = "none"
        if task.status in ("running", "stale") and task.total and task.total > task.current:
            rate = self._rate(task.id)
            if rate and rate > 0:
                remaining_s = (task.total - task.current) / rate
                task.rate = rate
                task.eta = datetime.fromtimestamp(
                    time.time() + remaining_s, tz=timezone.utc
                ).isoformat(timespec="seconds")
                task.eta_kind = "measured"
            elif task.declared_eta:
                task.eta = task.declared_eta
                task.eta_kind = "declared"
        elif task.status in ("pending", "blocked") and task.declared_eta:
            task.eta = task.declared_eta
            task.eta_kind = "declared"
        return task

    def snapshot(
        self,
        project: str,
        stale_after_s: int = DEFAULT_STALE_AFTER_S,
    ) -> dict[str, Any]:
        tasks: list[Task] = []
        for task_id in self.all_ids():
            task = self.get(task_id)
            if task is not None:
                tasks.append(self.hydrate(task, stale_after_s))
        tasks.sort(key=lambda task: (task.phase, task.id))

        status_by_id = {task.id: task.status for task in tasks}
        for task in tasks:
            task.blocked_by = [dep for dep in task.depends_on if status_by_id.get(dep) != "done"]
            task.ready = task.status == "pending" and not task.blocked_by

        active = [task for task in tasks if task.status != "cancelled"]
        scientific = [task for task in active if task.phase != "EXEC"]
        execution = [task for task in active if task.phase == "EXEC"]

        def weighted_progress(selected: list[Task]) -> float:
            weight_sum = sum(task.weight for task in selected) or 1.0
            return sum(task.weight * task.progress for task in selected) / weight_sum

        overall = weighted_progress(scientific)
        execution_progress = weighted_progress(execution) if execution else 0.0

        by_phase: dict[str, dict[str, float]] = {}
        for task in active:
            phase = by_phase.setdefault(
                task.phase or "misc", {"weight": 0.0, "weighted_progress": 0.0}
            )
            phase["weight"] += task.weight
            phase["weighted_progress"] += task.weight * task.progress
        phases = {
            key: {
                "progress": value["weighted_progress"] / value["weight"] if value["weight"] else 0.0
            }
            for key, value in by_phase.items()
        }

        counts: dict[str, int] = {}
        for task in tasks:
            counts[task.status] = counts.get(task.status, 0) + 1

        return {
            "project": project,
            "generated_at": now_iso(),
            "revision": self.revision(),
            "overall_progress": overall,
            "overall_kind": "effort-weighted scientific program gate completion",
            "science_gate_progress": overall,
            "execution_progress": execution_progress,
            "execution_kind": "effort-weighted current execution milestone completion",
            "phases": phases,
            "status_counts": counts,
            "tasks": [asdict(task) for task in tasks],
        }
