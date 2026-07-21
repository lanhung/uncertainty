"""Render a task snapshot into an LLM-friendly Markdown status report."""
from __future__ import annotations

from typing import Any


def _pct(value: float) -> str:
    return f"{100 * value:.0f}%"


def _eta(task: dict[str, Any]) -> str:
    value = task.get("eta")
    if not value:
        return "—"
    kind = task.get("eta_kind")
    if kind == "measured":
        return f"{value} (measured)"
    if kind == "declared":
        return f"{value} (rough)"
    return str(value)


def render(snapshot: dict[str, Any]) -> str:
    project = snapshot.get("project", "project")
    lines = [
        f"# {project} — live research status",
        "",
        f"_Generated: {snapshot.get('generated_at', '')}; revision: "
        f"{snapshot.get('revision', 0)}_",
        "",
        f"**Overall plan completion: {_pct(snapshot.get('overall_progress', 0))}.** "
        "This is effort-weighted execution progress, not scientific confidence.",
        "",
    ]

    counts = snapshot.get("status_counts", {})
    order = ["running", "stale", "blocked", "failed", "pending", "done", "cancelled"]
    if counts:
        lines.append(
            "Status counts — "
            + ", ".join(f"{status}: {counts[status]}" for status in order if counts.get(status))
        )
        lines.append("")

    tasks = snapshot.get("tasks", [])
    ready = [task for task in tasks if task.get("ready")]
    if ready:
        lines.append("## Next runnable")
        for task in ready[:12]:
            lines.append(f"- **{task['id']}** — {task.get('title', '')}")
        lines.append("")

    def add_block(title: str, statuses: set[str]) -> None:
        selected = [task for task in tasks if task.get("status") in statuses]
        if not selected:
            return
        lines.append(f"## {title}")
        for task in selected:
            lines.append(
                f"- **{task['id']}** — {task.get('title', '')} [{task.get('status')}]"
            )
            if task.get("total") is not None:
                lines.append(
                    f"  - progress: {_pct(task.get('progress', 0))} "
                    f"({task.get('current', 0):g}/{task.get('total', 0):g} "
                    f"{task.get('unit', '')}); ETA: {_eta(task)}"
                )
            if task.get("owner"):
                lines.append(
                    f"  - owner: {task['owner']}; attempt: {task.get('attempt', 0)}; "
                    f"run_id: {task.get('run_id') or '—'}"
                )
            if task.get("heartbeat_age_s") is not None and task.get("status") in {
                "running",
                "stale",
            }:
                lines.append(
                    f"  - heartbeat age: {task['heartbeat_age_s']:.0f} s"
                )
            if task.get("blocked_by"):
                lines.append(f"  - blocked by: {', '.join(task['blocked_by'])}")
            elif task.get("depends_on"):
                lines.append(f"  - depends on: {', '.join(task['depends_on'])}")
            if task.get("metrics"):
                metrics = ", ".join(
                    f"{key}={value}" for key, value in task["metrics"].items()
                )
                lines.append(f"  - metrics: {metrics}")
            if task.get("message"):
                lines.append(f"  - note: {task['message']}")
            links = task.get("artifact_links") or []
            if links:
                formatted = ", ".join(
                    f"[{item['label']}]({item['url']})" for item in links
                )
                lines.append(f"  - artifacts: {formatted}")
        lines.append("")

    add_block("Live now", {"running", "stale"})
    add_block("Blocked / needs a decision", {"blocked"})
    add_block("Failed", {"failed"})
    add_block("Pending", {"pending"})
    add_block("Done", {"done"})
    return "\n".join(lines).rstrip() + "\n"
