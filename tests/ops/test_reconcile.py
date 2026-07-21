from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import yaml

from orchestrator.reconcile import PlanError, reconcile, validate_plan
from orchestrator.store import Store


class ReconcileTests(unittest.TestCase):
    def test_validation_rejects_missing_dependencies_and_cycles(self) -> None:
        with self.assertRaises(PlanError):
            validate_plan({"tasks": [{"id": "A", "depends_on": ["missing"]}]})
        with self.assertRaises(PlanError):
            validate_plan(
                {
                    "tasks": [
                        {"id": "A", "depends_on": ["B"]},
                        {"id": "B", "depends_on": ["A"]},
                    ]
                }
            )

    def test_reconcile_preserves_runtime_progress(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan_path = root / "plan.yaml"
            plan_path.write_text(
                yaml.safe_dump(
                    {
                        "tasks": [
                            {"id": "A", "title": "old", "total": 10},
                            {"id": "B", "depends_on": ["A"]},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            store = Store(root / "state.db")
            result = reconcile(store, plan_path)
            self.assertEqual(set(result["created"]), {"A", "B"})
            store.start("A", "worker", 10, "samples", "run-1")
            store.progress("A", 4, 10, "working", None, "worker", "run-1")

            plan_path.write_text(
                yaml.safe_dump(
                    {
                        "tasks": [
                            {"id": "A", "title": "new", "total": 20},
                            {"id": "C", "depends_on": ["A"]},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            result = reconcile(store, plan_path)
            self.assertIn("A", result["updated"])
            self.assertIn("B", result["cancelled"])
            task = store.get("A")
            assert task is not None
            self.assertEqual(task.title, "new")
            self.assertEqual(task.total, 20)
            self.assertEqual(task.current, 4)
            self.assertEqual(task.status, "running")
            store.close()


if __name__ == "__main__":
    unittest.main()
