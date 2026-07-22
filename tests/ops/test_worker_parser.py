from __future__ import annotations

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock


class WorkerParserTests(unittest.TestCase):
    def test_outbox_drain_stops_after_first_transient_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            os.environ["RESEARCH_OPS_STATE_DIR"] = directory
            os.environ["RESEARCH_OPS_OUTBOX"] = str(Path(directory) / "outbox")
            os.environ["RESEARCH_OPS_CHECKPOINT_DIR"] = str(Path(directory) / "checkpoints")
            os.environ["RESEARCH_OPS_RUN_DIR"] = str(Path(directory) / "runs")
            path = Path(__file__).parents[2] / "worker" / "run_with_heartbeat.py"
            spec = importlib.util.spec_from_file_location("heartbeat_outbox_module", path)
            assert spec and spec.loader
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            heartbeat = module.Heartbeat(
                "T", 1, "checks", 30, module.DEFAULT_PROGRESS_RE, False, False
            )
            for index in range(3):
                heartbeat._buffer({"event": "progress", "index": index})

            with mock.patch.object(heartbeat, "_request", return_value="retry") as request:
                self.assertFalse(heartbeat.send({"event": "done"}))

            self.assertEqual(request.call_count, 1)
            self.assertEqual(len(heartbeat.outbox_file.read_text().splitlines()), 4)

    def test_low_level_timeout_is_treated_as_transient(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            os.environ["RESEARCH_OPS_STATE_DIR"] = directory
            os.environ["RESEARCH_OPS_OUTBOX"] = str(Path(directory) / "outbox")
            os.environ["RESEARCH_OPS_CHECKPOINT_DIR"] = str(Path(directory) / "checkpoints")
            os.environ["RESEARCH_OPS_RUN_DIR"] = str(Path(directory) / "runs")
            path = Path(__file__).parents[2] / "worker" / "run_with_heartbeat.py"
            spec = importlib.util.spec_from_file_location("heartbeat_timeout_module", path)
            assert spec and spec.loader
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            heartbeat = module.Heartbeat(
                "T", 1, "checks", 30, module.DEFAULT_PROGRESS_RE, False, False
            )

            with mock.patch.object(module.urllib.request, "urlopen", side_effect=TimeoutError):
                self.assertEqual(heartbeat._request({"event": "start"}), "retry")

    def test_force_start_is_forwarded_to_the_start_event(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            os.environ["RESEARCH_OPS_STATE_DIR"] = directory
            os.environ["RESEARCH_OPS_OUTBOX"] = str(Path(directory) / "outbox")
            os.environ["RESEARCH_OPS_CHECKPOINT_DIR"] = str(Path(directory) / "checkpoints")
            os.environ["RESEARCH_OPS_RUN_DIR"] = str(Path(directory) / "runs")
            path = Path(__file__).parents[2] / "worker" / "run_with_heartbeat.py"
            spec = importlib.util.spec_from_file_location("heartbeat_force_module", path)
            assert spec and spec.loader
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            heartbeat = module.Heartbeat(
                "T", 1, "checks", 30, module.DEFAULT_PROGRESS_RE, False, False
            )
            sent = []
            heartbeat.send = lambda body, **_kwargs: sent.append(body) or True
            heartbeat.start_reporting(force_start=True)
            heartbeat._stop.set()
            assert heartbeat._report_thread is not None
            heartbeat._report_thread.join(timeout=1)
            self.assertTrue(sent[0]["force"])

    def test_absolute_progress_does_not_regress(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            os.environ["RESEARCH_OPS_STATE_DIR"] = directory
            os.environ["RESEARCH_OPS_OUTBOX"] = str(Path(directory) / "outbox")
            os.environ["RESEARCH_OPS_CHECKPOINT_DIR"] = str(Path(directory) / "checkpoints")
            os.environ["RESEARCH_OPS_RUN_DIR"] = str(Path(directory) / "runs")
            path = Path(__file__).parents[2] / "worker" / "run_with_heartbeat.py"
            spec = importlib.util.spec_from_file_location("heartbeat_test_module", path)
            assert spec and spec.loader
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            heartbeat = module.Heartbeat(
                "T",
                None,
                "samples",
                30,
                module.DEFAULT_PROGRESS_RE,
                False,
                False,
            )
            heartbeat.observe("PROGRESS 40/100\n")
            heartbeat.observe("PROGRESS 2/100\n")
            heartbeat.observe("METRIC loss=1.25e-2\n")
            self.assertEqual(heartbeat.current, 40)
            self.assertEqual(heartbeat.total, 100)
            self.assertAlmostEqual(heartbeat.metrics["loss"], 0.0125)

    def test_successful_partial_stage_emits_terminal_block(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            os.environ["RESEARCH_OPS_STATE_DIR"] = directory
            os.environ["RESEARCH_OPS_OUTBOX"] = str(Path(directory) / "outbox")
            os.environ["RESEARCH_OPS_CHECKPOINT_DIR"] = str(Path(directory) / "checkpoints")
            os.environ["RESEARCH_OPS_RUN_DIR"] = str(Path(directory) / "runs")
            path = Path(__file__).parents[2] / "worker" / "run_with_heartbeat.py"
            spec = importlib.util.spec_from_file_location("heartbeat_partial_module", path)
            assert spec and spec.loader
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            heartbeat = module.Heartbeat(
                "EXEC-PARTIAL", 4, "components", 30, module.DEFAULT_PROGRESS_RE, False, False
            )
            emitted = []
            heartbeat.emit = lambda event, **kwargs: emitted.append((event, kwargs))
            heartbeat.finish(0, success_event="block", success_reason="one component accepted")
            self.assertEqual(emitted, [("block", {"reason": "one component accepted"})])


if __name__ == "__main__":
    unittest.main()
