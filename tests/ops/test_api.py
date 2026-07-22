from __future__ import annotations

import importlib
import os
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

import yaml
from fastapi.testclient import TestClient


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tempdir = tempfile.TemporaryDirectory()
        root = Path(cls.tempdir.name)
        plan = root / "plan.yaml"
        plan.write_text(
            yaml.safe_dump(
                {
                    "tasks": [
                        {"id": "A", "title": "first", "total": 2},
                        {"id": "B", "title": "second", "depends_on": ["A"]},
                    ]
                }
            ),
            encoding="utf-8",
        )
        config = root / "config.yaml"
        config.write_text(
            yaml.safe_dump(
                {
                    "project": "api-test",
                    "repo_dir": str(root),
                    "plan_path": "plan.yaml",
                    "state_dir": str(root / "state"),
                    "snapshot_repo_dir": str(root / "snapshot"),
                    "snapshot_every_s": 0,
                }
            ),
            encoding="utf-8",
        )
        os.environ["RESEARCH_OPS_CONFIG"] = str(config)
        os.environ["RESEARCH_OPS_TOKEN"] = "secret"
        for name in list(sys.modules):
            if name == "orchestrator.status_server":
                del sys.modules[name]
        cls.module = importlib.import_module("orchestrator.status_server")
        cls.client_context = TestClient(cls.module.app)
        cls.client = cls.client_context.__enter__()
        cls.headers = {"Authorization": "Bearer secret"}

    @classmethod
    def tearDownClass(cls) -> None:
        cls.client_context.__exit__(None, None, None)
        cls.module.store.close()
        cls.tempdir.cleanup()

    def report(self, payload):
        payload.setdefault("event_id", str(uuid.uuid4()))
        return self.client.post("/report", json=payload, headers=self.headers)

    def test_auth_and_dependency_enforcement(self) -> None:
        denied = self.client.post("/report", json={"task_id": "A", "event": "start"})
        self.assertEqual(denied.status_code, 401)
        blocked = self.report({"task_id": "B", "event": "start"})
        self.assertEqual(blocked.status_code, 409)

    def test_idempotent_event_and_normal_flow(self) -> None:
        event_id = str(uuid.uuid4())
        payload = {
            "task_id": "A",
            "event": "start",
            "event_id": event_id,
            "run_id": "run-a",
            "total": 2,
        }
        first = self.client.post("/report", json=payload, headers=self.headers)
        second = self.client.post("/report", json=payload, headers=self.headers)
        self.assertEqual(first.status_code, 200)
        self.assertTrue(second.json()["duplicate"])
        self.report(
            {
                "task_id": "A",
                "event": "progress",
                "run_id": "run-a",
                "current": 1,
            }
        )
        self.report({"task_id": "A", "event": "done", "run_id": "run-a"})
        start_b = self.report({"task_id": "B", "event": "start", "run_id": "run-b"})
        self.assertEqual(start_b.status_code, 200)

    def test_state_exposes_separate_science_and_execution_progress(self) -> None:
        response = self.client.get("/api/state")

        self.assertEqual(response.status_code, 200)
        snapshot = response.json()
        self.assertIn("science_gate_progress", snapshot)
        self.assertIn("execution_progress", snapshot)


if __name__ == "__main__":
    unittest.main()
