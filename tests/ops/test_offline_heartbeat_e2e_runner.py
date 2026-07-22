from __future__ import annotations

import json
import socket
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

from scripts import run_offline_heartbeat_e2e as runner


def protocol_payload() -> dict[str, object]:
    return {
        "schema_version": 1,
        "test_id": "OFFLINE-HEARTBEAT-E2E-v1",
        "status": "protocol_frozen_execution_pending",
        "task_id": runner.FROZEN_TASK_ID,
        "phase": "EXEC",
        "resource": runner.FROZEN_RESOURCE,
        "endpoint_during_run": runner.FROZEN_ENDPOINT,
        "steps": 8,
        "sleep_seconds": 6,
        "heartbeat_interval_seconds": 5,
        "state_root_rule": "dedicated_persistent_run_directory",
        "replay_mode": "dry_run_then_explicit_apply",
        "scientific_boundary": (
            "This regression must not change science-gate progress or scientific task state."
        ),
    }


class OfflineHeartbeatE2ERunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_protocol(self, payload: dict[str, object] | None = None) -> Path:
        path = self.root / "protocol.yaml"
        path.write_text(yaml.safe_dump(payload or protocol_payload()), encoding="utf-8")
        return path

    def test_protocol_freezes_identity_endpoint_and_science_boundary(self) -> None:
        protocol = runner.load_protocol(self.write_protocol())
        self.assertEqual(protocol.task_id, runner.FROZEN_TASK_ID)
        self.assertEqual(protocol.endpoint, "http://127.0.0.1:1")
        self.assertEqual(protocol.steps, 8)

        changed = protocol_payload()
        changed["endpoint_during_run"] = "https://control.example"
        with self.assertRaisesRegex(runner.OfflineE2EError, "safety mismatch"):
            runner.load_protocol(self.write_protocol(changed))
        changed = protocol_payload()
        changed["scientific_boundary"] = "credit this to science"
        with self.assertRaisesRegex(runner.OfflineE2EError, "science-gate"):
            runner.load_protocol(self.write_protocol(changed))

    def test_endpoint_must_be_frozen_and_actively_unreachable(self) -> None:
        with mock.patch.object(socket, "create_connection", side_effect=ConnectionRefusedError):
            runner.assert_endpoint_unreachable(runner.FROZEN_ENDPOINT)
        fake_connection = mock.Mock()
        with mock.patch.object(socket, "create_connection", return_value=fake_connection):
            with self.assertRaisesRegex(runner.OfflineE2EError, "unexpectedly reachable"):
                runner.assert_endpoint_unreachable(runner.FROZEN_ENDPOINT)
        fake_connection.close.assert_called_once()
        with self.assertRaisesRegex(runner.OfflineE2EError, "non-frozen"):
            runner.assert_endpoint_unreachable("http://127.0.0.1:2")

    def test_command_enforces_lease_offline_start_and_exact_demo(self) -> None:
        protocol = runner.load_protocol(self.write_protocol())
        command = runner.build_worker_command(
            protocol,
            repository_root=Path("/repo"),
            lock_root=Path("/locks"),
        )
        rendered = " ".join(command)
        self.assertIn("with_resource_lease.sh --resource ops-e2e", rendered)
        self.assertIn("--project uncertainty --task EXEC-HEARTBEAT-OFFLINE-E2E-v1", rendered)
        self.assertIn("run_with_heartbeat.py", rendered)
        self.assertIn("--allow-offline-start", command)
        self.assertIn("ops_demo_job.py --steps 8 --sleep 6.0", rendered)

    def test_finished_outbox_requires_identity_monotonicity_and_terminal_metric(self) -> None:
        outbox = self.root / "outbox.ndjson"
        events = [
            {
                "task_id": runner.FROZEN_TASK_ID,
                "run_id": "run-1",
                "event_id": "start",
                "event": "start",
                "total": 8,
            },
            {
                "task_id": runner.FROZEN_TASK_ID,
                "run_id": "run-1",
                "event_id": "progress",
                "event": "progress",
                "current": 4,
                "total": 8,
            },
            {
                "task_id": runner.FROZEN_TASK_ID,
                "run_id": "run-1",
                "event_id": "done",
                "event": "done",
                "current": 8,
                "total": 8,
                "metrics": {"demo_fraction": 1.0},
            },
        ]
        outbox.write_text("".join(json.dumps(event) + "\n" for event in events), encoding="utf-8")
        validated = runner.validate_finished_outbox(
            outbox,
            task_id=runner.FROZEN_TASK_ID,
            run_id="run-1",
            total=8,
        )
        self.assertEqual(len(validated.events), 3)

        events[-1]["metrics"] = {"demo_fraction": 0.5}
        outbox.write_text("".join(json.dumps(event) + "\n" for event in events), encoding="utf-8")
        with self.assertRaisesRegex(runner.OfflineE2EError, "demo_fraction"):
            runner.validate_finished_outbox(
                outbox,
                task_id=runner.FROZEN_TASK_ID,
                run_id="run-1",
                total=8,
            )

    def test_output_is_new_and_checksums_bind_regular_top_level_files(self) -> None:
        output = self.root / "artifact"
        runner.require_new_output_directory(output)
        with self.assertRaisesRegex(runner.OfflineE2EError, "must not already exist"):
            runner.require_new_output_directory(output)
        (output / "a.txt").write_text("a\n", encoding="utf-8")
        (output / "b.json").write_text("{}\n", encoding="utf-8")
        (output / "state").mkdir()
        runner.write_checksums(output)
        lines = (output / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
        self.assertEqual([line.split("  ", 1)[1] for line in lines], ["a.txt", "b.json"])

    def test_single_file_selection_rejects_ambiguous_state(self) -> None:
        state = self.root / "state"
        state.mkdir()
        with self.assertRaisesRegex(runner.OfflineE2EError, "found 0"):
            runner.select_single_file(state, "*.json", "metadata")
        (state / "one.json").write_text("{}", encoding="utf-8")
        self.assertEqual(runner.select_single_file(state, "*.json", "metadata").name, "one.json")
        (state / "two.json").write_text("{}", encoding="utf-8")
        with self.assertRaisesRegex(runner.OfflineE2EError, "found 2"):
            runner.select_single_file(state, "*.json", "metadata")


if __name__ == "__main__":
    unittest.main()
