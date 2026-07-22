from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from orchestrator.store import Store, Task


class StoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tempdir.name) / "state.db")
        self.store.upsert_static(Task(id="A", title="A", total=10))
        self.store.upsert_static(Task(id="B", title="B", depends_on=["A"]))

    def tearDown(self) -> None:
        self.store.close()
        self.tempdir.cleanup()

    def test_dependency_readiness_and_progress(self) -> None:
        snap = self.store.snapshot("test")
        by_id = {task["id"]: task for task in snap["tasks"]}
        self.assertTrue(by_id["A"]["ready"])
        self.assertFalse(by_id["B"]["ready"])
        self.assertEqual(by_id["B"]["blocked_by"], ["A"])

        self.store.start("A", "worker", 10, "samples", "run-1")
        self.store.progress("A", 4, 10, "working", {"loss": 1.2}, "worker", "run-1")
        task = self.store.get("A")
        assert task is not None
        self.assertEqual(task.current, 4)
        self.assertEqual(task.metrics["loss"], 1.2)
        self.store.finish("A", "done", "complete", None, "run-1")
        snap = self.store.snapshot("test")
        by_id = {item["id"]: item for item in snap["tasks"]}
        self.assertTrue(by_id["B"]["ready"])
        self.assertEqual(by_id["A"]["progress"], 1.0)

    def test_stale_run_cannot_overwrite_new_attempt(self) -> None:
        self.store.start("A", "worker-1", 10, "samples", "run-old")
        self.store.start("A", "worker-2", 10, "samples", "run-new")
        with self.assertRaises(ValueError):
            self.store.progress("A", 9, 10, None, None, "worker-1", "run-old")
        self.store.progress("A", 2, 10, None, None, "worker-2", "run-new")
        task = self.store.get("A")
        assert task is not None
        self.assertEqual(task.owner, "worker-2")
        self.assertEqual(task.current, 2)

    def test_event_idempotency(self) -> None:
        self.assertTrue(self.store.claim_event("evt-1"))
        self.assertFalse(self.store.claim_event("evt-1"))

    def test_stale_is_derived_without_destroying_runtime_state(self) -> None:
        self.store.start("A", "worker", 10, "samples", "run-1")
        task = self.store.get("A")
        assert task is not None
        task.updated_at = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(
            timespec="seconds"
        )
        self.store.upsert_static(task)
        snapshot = self.store.snapshot("test", stale_after_s=10)
        item = next(value for value in snapshot["tasks"] if value["id"] == "A")
        self.assertEqual(item["status"], "stale")
        persisted = self.store.get("A")
        assert persisted is not None
        self.assertEqual(persisted.status, "running")

    def test_execution_milestones_do_not_inflate_science_gate(self) -> None:
        self.store.upsert_static(Task(id="EXEC", title="runtime", phase="EXEC", total=4))
        self.store.start("A", "worker", 10, "samples", "run-a")
        self.store.progress("A", 4, 10, None, None, "worker", "run-a")
        self.store.start("EXEC", "worker", 4, "slices", "run-exec")
        self.store.finish("EXEC", "done", "four slices complete", None, "run-exec")

        snapshot = self.store.snapshot("test")

        self.assertEqual(snapshot["science_gate_progress"], 0.2)
        self.assertEqual(snapshot["overall_progress"], 0.2)
        self.assertEqual(snapshot["execution_progress"], 1.0)
        self.assertEqual(snapshot["phases"]["EXEC"]["progress"], 1.0)


if __name__ == "__main__":
    unittest.main()
