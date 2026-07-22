"""Validate and reconcile ``plan/plan.yaml`` into the live task ledger."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

try:
    from .store import Store, Task
except ImportError:  # direct script execution
    from store import Store, Task


class PlanError(ValueError):
    """Raised when the desired-state plan is internally inconsistent."""


def load_plan(path: str | Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as handle:
        plan = yaml.safe_load(handle) or {}
    if not isinstance(plan, dict):
        raise PlanError("plan root must be a mapping")
    return plan


def validate_plan(plan: dict[str, Any]) -> dict[str, Any]:
    tasks = plan.get("tasks")
    if not isinstance(tasks, list):
        raise PlanError("plan.tasks must be a list")

    by_id: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    for index, spec in enumerate(tasks):
        if not isinstance(spec, dict):
            errors.append(f"tasks[{index}] must be a mapping")
            continue
        task_id = spec.get("id")
        if not isinstance(task_id, str) or not task_id.strip():
            errors.append(f"tasks[{index}].id must be a non-empty string")
            continue
        if task_id in by_id:
            errors.append(f"duplicate task id: {task_id}")
        by_id[task_id] = spec
        weight = spec.get("weight", 1.0)
        try:
            if float(weight) <= 0:
                errors.append(f"{task_id}: weight must be > 0")
        except (TypeError, ValueError):
            errors.append(f"{task_id}: weight must be numeric")
        total = spec.get("total")
        if total is not None:
            try:
                if float(total) <= 0:
                    errors.append(f"{task_id}: total must be > 0 when set")
            except (TypeError, ValueError):
                errors.append(f"{task_id}: total must be numeric")
        depends_on = spec.get("depends_on", [])
        if not isinstance(depends_on, list) or not all(isinstance(dep, str) for dep in depends_on):
            errors.append(f"{task_id}: depends_on must be a list of task ids")

    for task_id, spec in by_id.items():
        for dep in spec.get("depends_on", []):
            if dep == task_id:
                errors.append(f"{task_id}: task cannot depend on itself")
            elif dep not in by_id:
                errors.append(f"{task_id}: missing dependency {dep}")

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(task_id: str, path: list[str]) -> None:
        if task_id in visited:
            return
        if task_id in visiting:
            cycle_start = path.index(task_id) if task_id in path else 0
            cycle = path[cycle_start:] + [task_id]
            errors.append("dependency cycle: " + " -> ".join(cycle))
            return
        visiting.add(task_id)
        path.append(task_id)
        for dep in by_id.get(task_id, {}).get("depends_on", []):
            if dep in by_id:
                visit(dep, path)
        path.pop()
        visiting.remove(task_id)
        visited.add(task_id)

    for task_id in by_id:
        visit(task_id, [])

    if errors:
        raise PlanError("; ".join(dict.fromkeys(errors)))
    return {
        "task_count": len(by_id),
        "phases": sorted({str(spec.get("phase", "misc")) for spec in by_id.values()}),
    }


def _static_signature(task: Task) -> dict[str, Any]:
    data = task.to_static()
    return {
        key: data[key]
        for key in (
            "title",
            "phase",
            "weight",
            "unit",
            "total",
            "depends_on",
            "declared_eta",
            "status",
        )
    }


def reconcile(store: Store, plan_path: str | Path) -> dict[str, Any]:
    plan = load_plan(plan_path)
    validation = validate_plan(plan)
    plan_tasks: list[dict[str, Any]] = plan["tasks"]
    plan_ids: set[str] = set()
    created: list[str] = []
    updated: list[str] = []
    unchanged: list[str] = []
    cancelled: list[str] = []

    for spec in plan_tasks:
        task_id = spec["id"]
        plan_ids.add(task_id)
        existing = store.get(task_id)
        if existing is None:
            task = Task(
                id=task_id,
                title=str(spec.get("title", "")),
                phase=str(spec.get("phase", "")),
                weight=float(spec.get("weight", 1.0)),
                unit=str(spec.get("unit", "units")),
                total=float(spec["total"]) if spec.get("total") is not None else None,
                depends_on=list(spec.get("depends_on", [])),
                declared_eta=spec.get("declared_eta"),
                status="pending",
            )
            store.upsert_static(task)
            created.append(task_id)
            continue

        before = _static_signature(existing)
        existing.title = str(spec.get("title", ""))
        existing.phase = str(spec.get("phase", ""))
        existing.weight = float(spec.get("weight", 1.0))
        existing.unit = str(spec.get("unit", "units"))
        existing.total = float(spec["total"]) if spec.get("total") is not None else None
        existing.depends_on = list(spec.get("depends_on", []))
        existing.declared_eta = spec.get("declared_eta")
        if existing.status == "cancelled":
            existing.status = "pending"
        after = _static_signature(existing)
        if before == after:
            unchanged.append(task_id)
        else:
            store.upsert_static(existing)
            updated.append(task_id)

    for task_id in store.all_ids():
        if task_id in plan_ids:
            continue
        task = store.get(task_id)
        if task and task.status != "cancelled":
            store.finish(
                task_id,
                "cancelled",
                "removed from desired-state plan",
                None,
                None,
            )
            cancelled.append(task_id)

    return {
        "valid": True,
        "validation": validation,
        "created": created,
        "updated": updated,
        "unchanged": unchanged,
        "cancelled": cancelled,
    }


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser()
    parser.add_argument("plan")
    args = parser.parse_args()
    loaded = load_plan(args.plan)
    print(json.dumps(validate_plan(loaded), indent=2, ensure_ascii=False))
