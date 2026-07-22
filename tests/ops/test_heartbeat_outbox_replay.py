from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import yaml

from scripts import replay_heartbeat_outbox as replay
from scripts.validate_offline_heartbeat_e2e import validate_bundle

TASK_ID = "EXEC-HEARTBEAT-OFFLINE-E2E-v1"
RUN_ID = "offline-run-1"


def _events() -> list[dict[str, object]]:
    return [
        {
            "task_id": TASK_ID,
            "run_id": RUN_ID,
            "event_id": "event-start",
            "event": "start",
            "owner": "worker",
            "total": 8,
            "unit": "checks",
        },
        {
            "task_id": TASK_ID,
            "run_id": RUN_ID,
            "event_id": "event-progress",
            "event": "progress",
            "owner": "worker",
            "current": 4,
            "total": 8,
        },
        {
            "task_id": TASK_ID,
            "run_id": RUN_ID,
            "event_id": "event-done",
            "event": "done",
            "owner": "worker",
            "current": 8,
            "total": 8,
            "metrics": {"demo_fraction": 1.0},
        },
    ]


def _write_outbox(path: Path, events: list[dict[str, object]] | None = None) -> bytes:
    raw = b"".join(
        json.dumps(event, sort_keys=True).encode() + b"\n" for event in (events or _events())
    )
    path.write_bytes(raw)
    return raw


def _write_plan(path: Path, *, phase: str = "EXEC") -> None:
    path.write_text(
        yaml.safe_dump({"tasks": [{"id": TASK_ID, "title": "offline E2E", "phase": phase}]}),
        encoding="utf-8",
    )


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def replay_validator_files() -> set[str]:
    return {
        "run_manifest.json",
        "runner.log",
        "checkpoint-midrun.json",
        "checkpoint-final.json",
        "run_metadata.json",
        "lease-midrun.json",
        "outbox-before-replay.ndjson",
        "replay_report.json",
        "resource_report.json",
        "SHA256SUMS",
    }


class HeartbeatOutboxReplayTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary_directory = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._temporary_directory.name)

    def tearDown(self) -> None:
        self._temporary_directory.cleanup()

    def test_dry_run_requires_exec_and_does_not_modify_outbox(self) -> None:
        outbox = self.tmp_path / "outbox.ndjson"
        original = _write_outbox(outbox)
        plan = self.tmp_path / "plan.yaml"
        _write_plan(plan)

        result = replay.dry_run(outbox, plan)

        self.assertEqual(result["status"], "validated")
        self.assertEqual(result["event_count"], 3)
        self.assertEqual(result["sha256"], hashlib.sha256(original).hexdigest())
        self.assertEqual(outbox.read_bytes(), original)
        _write_plan(plan, phase="P0")
        with self.assertRaisesRegex(replay.ReplayError, "non-EXEC"):
            replay.dry_run(outbox, plan)
        self.assertEqual(outbox.read_bytes(), original)

    def test_invalid_event_contract_is_rejected_without_mutation(self) -> None:
        mutations = [
            (
                lambda events: events.__setitem__(0, {**events[0], "event": "progress"}),
                "first",
            ),
            (
                lambda events: events.__setitem__(2, {**events[2], "event": "progress"}),
                "last",
            ),
            (lambda events: events[1].update(run_id="other"), "run_id"),
            (lambda events: events[1].update(task_id="other"), "task_id"),
            (lambda events: events[1].update(event_id="event-start"), "unique"),
        ]
        for index, (mutator, match) in enumerate(mutations):
            with self.subTest(match=match):
                events = _events()
                mutator(events)
                outbox = self.tmp_path / f"outbox-{index}.ndjson"
                original = _write_outbox(outbox, events)
                with self.assertRaisesRegex(replay.ReplayError, match):
                    replay.validate_outbox(outbox)
                self.assertEqual(outbox.read_bytes(), original)

    def test_bad_json_is_retained(self) -> None:
        outbox = self.tmp_path / "outbox.ndjson"
        outbox.write_bytes(b'{"event":"start"}\nnot-json\n')
        original = outbox.read_bytes()
        with self.assertRaisesRegex(replay.ReplayError, "not valid"):
            replay.validate_outbox(outbox)
        self.assertEqual(outbox.read_bytes(), original)

    def test_apply_replays_in_order_archives_and_accepts_duplicates(self) -> None:
        outbox = self.tmp_path / "outbox.ndjson"
        original = _write_outbox(outbox)
        plan = self.tmp_path / "plan.yaml"
        _write_plan(plan)
        received: list[str] = []

        def sender(_endpoint: str, token: str, event: dict[str, object]):
            self.assertEqual(token, "token-from-environment")
            received.append(str(event["event_id"]))
            return {"ok": True, "duplicate": event["event"] == "progress"}

        result = replay.replay_outbox(
            outbox,
            plan_path=plan,
            endpoint="http://control.invalid",
            token="token-from-environment",
            archive_dir=self.tmp_path / "archive",
            sender=sender,
        )

        self.assertEqual(received, ["event-start", "event-progress", "event-done"])
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["duplicate_acknowledgements"], 1)
        self.assertTrue(result["outbox_drained"])
        self.assertFalse(outbox.exists())
        archive = Path(result["archive"])
        self.assertEqual(archive.read_bytes(), original)
        self.assertTrue(
            archive.with_suffix(archive.suffix + ".sha256")
            .read_text()
            .startswith(hashlib.sha256(original).hexdigest())
        )

    def test_completed_unlink_window_is_recoverable_from_state(self) -> None:
        outbox = self.tmp_path / "outbox.ndjson"
        _write_outbox(outbox)
        plan = self.tmp_path / "plan.yaml"
        _write_plan(plan)
        validated = replay.validate_outbox(outbox)
        archive = replay.archive_outbox(validated, self.tmp_path / "archive")
        state_path = replay._state_path(outbox)
        replay._write_replay_state(state_path, validated, archive)
        outbox.unlink()

        def must_not_send(*_args):
            self.fail("a completed replay must not resend")

        result = replay.replay_outbox(
            outbox,
            plan_path=plan,
            endpoint="http://control.invalid",
            token="secret",
            archive_dir=self.tmp_path / "archive",
            sender=must_not_send,
        )
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["events_replayed_this_invocation"], 0)
        self.assertFalse(state_path.exists())

    def test_failure_keeps_unacknowledged_tail_and_can_resume(self) -> None:
        for index, failure in enumerate(("http-401", "http-503", "connection")):
            with self.subTest(failure=failure):
                case_dir = self.tmp_path / str(index)
                case_dir.mkdir()
                outbox = case_dir / "outbox.ndjson"
                original = _write_outbox(outbox)
                original_lines = original.splitlines(keepends=True)
                plan = case_dir / "plan.yaml"
                _write_plan(plan)
                calls = 0

                def failing_sender(_endpoint: str, _token: str, _event: dict[str, object]):
                    nonlocal calls
                    calls += 1
                    if calls == 2:
                        raise replay.ReplayTransportError(failure)
                    return {"ok": True}

                with self.assertRaisesRegex(replay.ReplayTransportError, failure):
                    replay.replay_outbox(
                        outbox,
                        plan_path=plan,
                        endpoint="http://control.invalid",
                        token="secret",
                        archive_dir=case_dir / "archive",
                        sender=failing_sender,
                    )

                self.assertEqual(outbox.read_bytes(), b"".join(original_lines[1:]))
                archived = next((case_dir / "archive").glob("*.ndjson"))
                self.assertEqual(archived.read_bytes(), original)
                resumed: list[str] = []

                def succeeding_sender(_endpoint: str, _token: str, event: dict[str, object]):
                    resumed.append(str(event["event_id"]))
                    return {"ok": True}

                result = replay.replay_outbox(
                    outbox,
                    plan_path=plan,
                    endpoint="http://control.invalid",
                    token="secret",
                    archive_dir=case_dir / "archive",
                    sender=succeeding_sender,
                )
                self.assertEqual(resumed, ["event-progress", "event-done"])
                self.assertEqual(result["events_replayed_this_invocation"], 2)
                self.assertFalse(outbox.exists())

    def test_offline_validator_accepts_complete_bundle(self) -> None:
        outbox = self.tmp_path / "outbox-before-replay.ndjson"
        outbox_raw = _write_outbox(outbox)
        _write_json(
            self.tmp_path / "run_manifest.json",
            {
                "schema_version": 1,
                "task_id": TASK_ID,
                "run_id": RUN_ID,
                "phase": "EXEC",
                "total": 8,
                "scientific_gate_credit": 0,
            },
        )
        _write_json(
            self.tmp_path / "checkpoint-midrun.json",
            {"task_id": TASK_ID, "run_id": RUN_ID, "current": 3, "total": 8},
        )
        _write_json(
            self.tmp_path / "checkpoint-final.json",
            {"task_id": TASK_ID, "run_id": RUN_ID, "current": 8, "total": 8},
        )
        _write_json(
            self.tmp_path / "run_metadata.json",
            {"task_id": TASK_ID, "run_id": RUN_ID, "command": ["demo"], "pid": 123},
        )
        _write_json(
            self.tmp_path / "lease-midrun.json",
            {
                "task_id": TASK_ID,
                "resource": "ops-e2e",
                "project": "uncertainty",
                "lease_id": "lease-1",
            },
        )
        _write_json(
            self.tmp_path / "replay_report.json",
            {
                "task_id": TASK_ID,
                "run_id": RUN_ID,
                "status": "completed",
                "outbox_drained": True,
                "event_count": 3,
                "archive_sha256": hashlib.sha256(outbox_raw).hexdigest(),
            },
        )
        _write_json(
            self.tmp_path / "resource_report.json",
            {
                "wall_seconds": 50,
                "worker_hours": 0.014,
                "cpu_core_hours": 0.001,
                "estimated_cost_cny": 0.04,
                "failure_count": 0,
            },
        )
        (self.tmp_path / "runner.log").write_text(
            "lease-acquired\nPROGRESS 8/8\nlease-released\n", encoding="utf-8"
        )
        checksum_names = sorted(name for name in replay_validator_files() if name != "SHA256SUMS")
        (self.tmp_path / "SHA256SUMS").write_text(
            "".join(
                f"{hashlib.sha256((self.tmp_path / name).read_bytes()).hexdigest()}  {name}\n"
                for name in checksum_names
            ),
            encoding="utf-8",
        )

        report = validate_bundle(self.tmp_path)
        self.assertEqual(report["status"], "accepted")
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["scientific_gate_credit"], 0)


if __name__ == "__main__":
    unittest.main()
