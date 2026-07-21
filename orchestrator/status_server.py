"""Research operations control plane.

The server is the only writer to the SQLite ledger.  It accepts authenticated
worker heartbeats, serves a live dashboard, reconciles the declarative plan,
and publishes a durable read-only snapshot to a separate Git status branch.
"""
from __future__ import annotations

import asyncio
import hmac
import json
import os
import re
import subprocess
import sys
import threading
from contextlib import asynccontextmanager
from pathlib import Path, PurePosixPath
from typing import Any, Literal, Optional, Union
from urllib.parse import quote, urlparse

import yaml
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from pydantic import BaseModel, ConfigDict, Field

try:
    from . import summarize
    from .reconcile import PlanError, reconcile as run_reconcile
    from .store import DEFAULT_STALE_AFTER_S, Store
except ImportError:  # direct script execution
    import summarize
    from reconcile import PlanError, reconcile as run_reconcile
    from store import DEFAULT_STALE_AFTER_S, Store

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = Path(
    os.environ.get("RESEARCH_OPS_CONFIG", ROOT / "project.config.yaml")
).expanduser()


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return {}
    with open(CONFIG_PATH, encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle) or {}
    if not isinstance(loaded, dict):
        raise RuntimeError(f"config must be a mapping: {CONFIG_PATH}")
    return loaded


CFG = load_config()
PROJECT = str(CFG.get("project", "project"))
REPO_DIR = Path(os.environ.get("RESEARCH_OPS_REPO_DIR", CFG.get("repo_dir", ROOT))).expanduser()
PLAN_PATH = REPO_DIR / str(CFG.get("plan_path", "plan/plan.yaml"))
STATE_DIR = Path(
    os.environ.get("RESEARCH_OPS_STATE_DIR", CFG.get("state_dir", ROOT / "state"))
).expanduser()
SNAPSHOT_REPO_DIR = Path(
    os.environ.get(
        "RESEARCH_OPS_SNAPSHOT_REPO",
        CFG.get("snapshot_repo_dir", REPO_DIR),
    )
).expanduser()
DB_PATH = STATE_DIR / "state.db"
STATE_DIR.mkdir(parents=True, exist_ok=True)
STALE_AFTER = int(CFG.get("stale_after_s", DEFAULT_STALE_AFTER_S))
SNAPSHOT_EVERY = int(CFG.get("snapshot_every_s", 180))
STATUS_BRANCH = str(CFG.get("status_branch", ""))
REPO_WEB_URL = str(CFG.get("repo_web_url", "")).rstrip("/")
CODE_BRANCH = str(CFG.get("code_branch", "main"))
TOKEN = os.environ.get("RESEARCH_OPS_TOKEN", "")
ALLOW_UNAUTH_WRITES = os.environ.get(
    "RESEARCH_OPS_ALLOW_UNAUTHENTICATED_WRITES", "0"
) == "1"
ALLOW_UNPLANNED = os.environ.get("RESEARCH_OPS_ALLOW_UNPLANNED_TASKS", "0") == "1"
DASHBOARD_HTML = (Path(__file__).parent / "dashboard.html").read_text(encoding="utf-8")
TASK_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
SNAPSHOT_LOCK = threading.Lock()

store = Store(DB_PATH)
store.set_meta("project", PROJECT)


def check_auth(authorization: Optional[str]) -> None:
    if not TOKEN:
        if ALLOW_UNAUTH_WRITES:
            return
        raise HTTPException(
            status_code=503,
            detail=(
                "write API disabled: configure RESEARCH_OPS_TOKEN or explicitly set "
                "RESEARCH_OPS_ALLOW_UNAUTHENTICATED_WRITES=1"
            ),
        )
    supplied = authorization or ""
    expected = f"Bearer {TOKEN}"
    if not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="bad or missing bearer token")


MetricValue = Union[float, int, str, bool, None]


class Report(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str = Field(min_length=1, max_length=128)
    event: Literal[
        "start",
        "progress",
        "done",
        "fail",
        "block",
        "cancel",
        "note",
        "artifact",
    ]
    event_id: Optional[str] = Field(default=None, max_length=128)
    run_id: Optional[str] = Field(default=None, max_length=128)
    owner: Optional[str] = Field(default=None, max_length=128)
    current: Optional[float] = None
    total: Optional[float] = None
    unit: Optional[str] = Field(default=None, max_length=64)
    message: Optional[str] = Field(default=None, max_length=2000)
    reason: Optional[str] = Field(default=None, max_length=2000)
    metrics: Optional[dict[str, MetricValue]] = None
    artifact: Optional[str] = Field(default=None, max_length=1000)
    force: bool = False


def _task_or_404(task_id: str):
    if not TASK_ID_RE.fullmatch(task_id):
        raise HTTPException(status_code=400, detail="invalid task id")
    task = store.get(task_id)
    if task is None and not ALLOW_UNPLANNED:
        raise HTTPException(
            status_code=404,
            detail=f"task {task_id!r} is not in the reconciled plan",
        )
    return task


def _incomplete_dependencies(task_id: str) -> list[str]:
    task = store.get(task_id)
    if task is None:
        return []
    blocked: list[str] = []
    for dependency in task.depends_on:
        dep_task = store.get(dependency)
        if dep_task is None or dep_task.status != "done":
            blocked.append(dependency)
    return blocked


def _normalize_artifact(path: str) -> str:
    parsed = urlparse(path)
    if parsed.scheme in {"http", "https"}:
        return path
    if parsed.scheme or parsed.netloc:
        raise HTTPException(status_code=400, detail="artifact URL scheme not allowed")
    posix = PurePosixPath(path)
    if posix.is_absolute() or ".." in posix.parts:
        raise HTTPException(
            status_code=400,
            detail="artifact must be a repository-relative path or https URL",
        )
    normalized = str(posix)
    if normalized in {"", "."}:
        raise HTTPException(status_code=400, detail="empty artifact path")
    return normalized


def _artifact_link(path: str) -> dict[str, str]:
    parsed = urlparse(path)
    if parsed.scheme in {"http", "https"}:
        return {"label": path, "url": path}
    if REPO_WEB_URL:
        url = f"{REPO_WEB_URL}/blob/{quote(CODE_BRANCH, safe='')}/{quote(path, safe='/')}"
    else:
        url = path
    return {"label": path, "url": url}


def _enrich_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    snapshot["repo_web_url"] = REPO_WEB_URL
    snapshot["code_branch"] = CODE_BRANCH
    snapshot["status_branch"] = STATUS_BRANCH
    for task in snapshot.get("tasks", []):
        task["artifact_links"] = [
            _artifact_link(path) for path in task.get("artifacts", [])
        ]
    return snapshot


def current_snapshot() -> dict[str, Any]:
    return _enrich_snapshot(store.snapshot(PROJECT, STALE_AFTER))


@asynccontextmanager
async def lifespan(_: FastAPI):
    if PLAN_PATH.exists():
        try:
            run_reconcile(store, PLAN_PATH)
        except Exception as exc:  # noqa: BLE001
            print(f"[startup] reconcile failed: {exc}", file=sys.stderr)
    task: Optional[asyncio.Task] = None
    if SNAPSHOT_EVERY > 0:
        task = asyncio.create_task(_snapshot_loop())
    yield
    if task is not None:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(title="research-ops status server", lifespan=lifespan)


@app.get("/", response_class=HTMLResponse)
def dashboard() -> str:
    return DASHBOARD_HTML


@app.get("/healthz")
def health() -> dict[str, Any]:
    return {
        "ok": True,
        "project": PROJECT,
        "revision": store.revision(),
        "plan_exists": PLAN_PATH.exists(),
        "write_auth_configured": bool(TOKEN) or ALLOW_UNAUTH_WRITES,
        "snapshot_repo": str(SNAPSHOT_REPO_DIR),
        "status_branch": STATUS_BRANCH,
    }


@app.get("/api/state")
def api_state() -> JSONResponse:
    return JSONResponse(
        current_snapshot(),
        headers={"Cache-Control": "no-store, max-age=0"},
    )


@app.get("/api/summary", response_class=PlainTextResponse)
def api_summary() -> str:
    return summarize.render(current_snapshot())


@app.post("/report")
def report(payload: Report, authorization: Optional[str] = Header(default=None)) -> dict[str, Any]:
    check_auth(authorization)
    task = _task_or_404(payload.task_id)
    if not store.claim_event(payload.event_id):
        return {
            "ok": True,
            "duplicate": True,
            "task_id": payload.task_id,
            "event": payload.event,
        }

    try:
        if payload.event == "start":
            blocked_by = _incomplete_dependencies(payload.task_id)
            if blocked_by and not payload.force:
                raise HTTPException(
                    status_code=409,
                    detail={"message": "dependencies incomplete", "blocked_by": blocked_by},
                )
            store.start(
                payload.task_id,
                payload.owner,
                payload.total,
                payload.unit,
                payload.run_id,
            )
        elif payload.event == "progress":
            if payload.current is None:
                raise HTTPException(status_code=400, detail="progress requires current")
            store.progress(
                payload.task_id,
                payload.current,
                payload.total,
                payload.message,
                payload.metrics,
                payload.owner,
                payload.run_id,
            )
        elif payload.event == "done":
            store.finish(
                payload.task_id,
                "done",
                payload.message,
                payload.metrics,
                payload.run_id,
            )
        elif payload.event == "fail":
            store.finish(
                payload.task_id,
                "failed",
                payload.reason or payload.message,
                payload.metrics,
                payload.run_id,
            )
        elif payload.event == "block":
            store.finish(
                payload.task_id,
                "blocked",
                payload.reason or payload.message,
                payload.metrics,
                payload.run_id,
            )
        elif payload.event == "cancel":
            store.finish(
                payload.task_id,
                "cancelled",
                payload.reason or payload.message,
                payload.metrics,
                payload.run_id,
            )
        elif payload.event == "note":
            store.note(payload.task_id, payload.message or "")
        elif payload.event == "artifact":
            if not payload.artifact:
                raise HTTPException(status_code=400, detail="artifact requires a path")
            store.add_artifact(payload.task_id, _normalize_artifact(payload.artifact))
        else:  # pragma: no cover - Literal already validates
            raise HTTPException(status_code=400, detail="unknown event")
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return {
        "ok": True,
        "task_id": payload.task_id,
        "event": payload.event,
        "revision": store.revision(),
        "known_before_event": task is not None,
    }


@app.post("/reconcile")
def reconcile_endpoint(
    authorization: Optional[str] = Header(default=None),
) -> dict[str, Any]:
    check_auth(authorization)
    if not PLAN_PATH.exists():
        raise HTTPException(status_code=404, detail=f"plan not found: {PLAN_PATH}")
    try:
        return run_reconcile(store, PLAN_PATH)
    except PlanError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/snapshot")
def snapshot_endpoint(
    authorization: Optional[str] = Header(default=None),
) -> dict[str, Any]:
    check_auth(authorization)
    return do_snapshot(force=True)


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(SNAPSHOT_REPO_DIR), *args],
        capture_output=True,
        text=True,
        timeout=60,
    )


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    os.replace(temporary, path)


def _git_detail(result: subprocess.CompletedProcess[str]) -> str:
    return (result.stderr or result.stdout or "").strip()[:800]


def do_snapshot(*, force: bool = False) -> dict[str, Any]:
    if not SNAPSHOT_LOCK.acquire(blocking=False):
        return {"snapshotted": False, "pushed": False, "reason": "snapshot already running"}
    try:
        snapshot = current_snapshot()
        revision = int(snapshot.get("revision", 0))
        last_revision = int(store.get_meta("last_snapshot_revision", "-1") or -1)
        has_live = any(
            task.get("status") in {"running", "stale"}
            for task in snapshot.get("tasks", [])
        )
        if not force and revision == last_revision and not has_live:
            return {
                "snapshotted": False,
                "pushed": False,
                "reason": "no state changes",
                "revision": revision,
            }

        snapshot_repo = SNAPSHOT_REPO_DIR
        state_dir = snapshot_repo / "state"
        docs_dir = snapshot_repo / "docs"
        state_dir.mkdir(parents=True, exist_ok=True)
        docs_dir.mkdir(parents=True, exist_ok=True)

        if (snapshot_repo / ".git").exists():
            branch = _git("branch", "--show-current")
            actual_branch = branch.stdout.strip()
            if STATUS_BRANCH and actual_branch != STATUS_BRANCH:
                return {
                    "snapshotted": False,
                    "pushed": False,
                    "reason": (
                        f"snapshot repo is on {actual_branch!r}, expected {STATUS_BRANCH!r}"
                    ),
                }
            pull = _git("pull", "--rebase", "--autostash")
            if pull.returncode != 0:
                return {
                    "snapshotted": False,
                    "pushed": False,
                    "reason": "git pull failed",
                    "detail": _git_detail(pull),
                }

        encoded = json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n"
        _atomic_write(state_dir / "tasks.json", encoded)
        _atomic_write(state_dir / "SUMMARY.md", summarize.render(snapshot))
        _atomic_write(docs_dir / "index.html", DASHBOARD_HTML)
        _atomic_write(docs_dir / "tasks.json", encoded)
        _atomic_write(snapshot_repo / ".nojekyll", "")

        if not (snapshot_repo / ".git").exists():
            store.set_meta("last_snapshot_revision", str(revision))
            return {
                "snapshotted": True,
                "pushed": False,
                "reason": "snapshot directory is not a git repository",
                "revision": revision,
            }

        _git("config", "user.name", "research-ops-bot")
        _git("config", "user.email", "research-ops@users.noreply.github.com")
        add = _git(
            "add",
            ".nojekyll",
            "state/tasks.json",
            "state/SUMMARY.md",
            "docs/index.html",
            "docs/tasks.json",
        )
        if add.returncode != 0:
            return {
                "snapshotted": True,
                "pushed": False,
                "reason": "git add failed",
                "detail": _git_detail(add),
            }
        status = _git("status", "--porcelain")
        if not status.stdout.strip():
            store.set_meta("last_snapshot_revision", str(revision))
            return {
                "snapshotted": True,
                "pushed": False,
                "reason": "no file changes",
                "revision": revision,
            }

        commit = _git(
            "commit",
            "-m",
            f"status: revision {revision} {snapshot['generated_at']} [skip ci]",
        )
        if commit.returncode != 0:
            return {
                "snapshotted": True,
                "pushed": False,
                "reason": "git commit failed",
                "detail": _git_detail(commit),
            }
        push = _git("push")
        if push.returncode != 0:
            return {
                "snapshotted": True,
                "pushed": False,
                "reason": "git push failed",
                "detail": _git_detail(push),
            }
        store.set_meta("last_snapshot_revision", str(revision))
        return {
            "snapshotted": True,
            "pushed": True,
            "revision": revision,
            "commit": _git("rev-parse", "HEAD").stdout.strip(),
        }
    finally:
        SNAPSHOT_LOCK.release()


async def _snapshot_loop() -> None:
    while True:
        await asyncio.sleep(SNAPSHOT_EVERY)
        try:
            result = await asyncio.to_thread(do_snapshot)
            if result.get("reason") not in {"no state changes", "no file changes"}:
                print(f"[snapshot] {result}")
        except Exception as exc:  # noqa: BLE001
            print(f"[snapshot] failed: {exc}", file=sys.stderr)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "snapshot":
        print(json.dumps(do_snapshot(force=True), indent=2, ensure_ascii=False))
    elif len(sys.argv) > 1 and sys.argv[1] == "reconcile":
        print(
            json.dumps(
                run_reconcile(store, PLAN_PATH),
                indent=2,
                ensure_ascii=False,
            )
        )
    else:
        if not TOKEN and not ALLOW_UNAUTH_WRITES:
            raise SystemExit(
                "RESEARCH_OPS_TOKEN is required for the write API. "
                "Use scripts/bootstrap_vultr.sh or set the environment variable."
            )
        import uvicorn

        uvicorn.run(
            app,
            host=os.environ.get("RESEARCH_OPS_HOST", "0.0.0.0"),
            port=int(os.environ.get("RESEARCH_OPS_PORT", "8787")),
            log_level=os.environ.get("RESEARCH_OPS_LOG_LEVEL", "info"),
        )
