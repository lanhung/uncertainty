from __future__ import annotations

import importlib.util
import tempfile
import unittest
import zipfile
from pathlib import Path


SCRIPT = Path(__file__).parents[2] / "scripts" / "render_local_topology_bundle.py"
SPEC = importlib.util.spec_from_file_location("render_local_topology_bundle", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


INVENTORY = """\
PROJECT_SLUG=uncertainty
PROJECT_PORT=8787
CONTROL_SSH_ALIAS=vultr-research
CONTROL_PUBLIC_HOST=192.0.2.10
CONTROL_SSH_PORT=22
CONTROL_SSH_USER=root
AUTODL1_ALIAS=autodl-westb-01
AUTODL1_HOST=worker-a.example.test
AUTODL1_PORT=22001
AUTODL1_USER=root
AUTODL1_NODE_NAME=autodl-westb-01
AUTODL1_REGION=westb
AUTODL2_ALIAS=autodl-bjb1-01
AUTODL2_HOST=worker-b.example.test
AUTODL2_PORT=22002
AUTODL2_USER=root
AUTODL2_NODE_NAME=autodl-bjb1-01
AUTODL2_REGION=bjb1
AUTODL_KEY_DIR=/root/.ssh/research-workers
"""


class LocalTopologyBundleTests(unittest.TestCase):
    def test_render_creates_reproducible_local_helpers(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inventory = root / "hosts.local.env"
            output = root / "out"
            archive = root / "bundle.zip"
            inventory.write_text(INVENTORY, encoding="utf-8")

            result = MODULE.render(inventory, output, archive, force=False)

            self.assertEqual(result["project"], "uncertainty")
            self.assertEqual(len(result["archive_sha256"]), 64)
            self.assertTrue(archive.is_file())
            self.assertEqual((output / "hosts.local.env").stat().st_mode & 0o777, 0o600)
            self.assertEqual(
                (output / "bootstrap_autodl-westb-01.sh").stat().st_mode & 0o777,
                0o700,
            )
            control_config = (output / "laptop_ssh_config.snippet").read_text(
                encoding="utf-8"
            )
            self.assertIn("HostName 192.0.2.10", control_config)
            wrapper = (output / "bootstrap_autodl-bjb1-01.sh").read_text(
                encoding="utf-8"
            )
            self.assertIn("AUTODL_REGION=bjb1", wrapper)
            self.assertIn("WORKER_ROLE=elastic", wrapper)
            with zipfile.ZipFile(archive) as bundle:
                names = set(bundle.namelist())
            self.assertIn("SHA256SUMS", names)
            self.assertIn("README_LOCAL.md", names)
            self.assertNotIn("RESEARCH_OPS_TOKEN", archive.read_bytes().decode("latin1"))

    def test_rejects_secret_or_unknown_inventory_fields(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            inventory = Path(directory) / "hosts.local.env"
            inventory.write_text(
                INVENTORY + "RESEARCH_OPS_TOKEN=must-not-be-bundled\n",
                encoding="utf-8",
            )
            with self.assertRaises(MODULE.InventoryError):
                MODULE.load_inventory(inventory)

    def test_nonempty_output_requires_force(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inventory = root / "hosts.local.env"
            output = root / "out"
            archive = root / "bundle.zip"
            inventory.write_text(INVENTORY, encoding="utf-8")
            output.mkdir()
            (output / "unrelated.txt").write_text("preserve me", encoding="utf-8")
            with self.assertRaises(MODULE.InventoryError):
                MODULE.render(inventory, output, archive, force=False)


if __name__ == "__main__":
    unittest.main()
