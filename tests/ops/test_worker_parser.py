from __future__ import annotations

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path


class WorkerParserTests(unittest.TestCase):
    def test_force_start_is_forwarded_to_the_start_event(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            os.environ["RESEARCH_OPS_STATE_DIR"] = directory
            os.environ["RESEARCH_OPS_OUTBOX"] = str(Path(directory) / "outbox")
            os.environ["RESEARCH_OPS_CHECKPOINT_DIR"] = str(
                Path(directory) / "checkpoints"
            )
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


if __name__ == "__main__":
    unittest.main()
