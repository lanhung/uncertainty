from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class TopologyContractTests(unittest.TestCase):
    def test_vultr_control_instance_is_project_scoped(self) -> None:
        script = (ROOT / "scripts" / "bootstrap_vultr.sh").read_text(encoding="utf-8")
        self.assertIn('SERVICE_NAME="${RESEARCH_OPS_SERVICE_NAME:-research-ops-${PROJECT_SLUG}}"', script)
        self.assertIn('/var/lib/research-ops/${PROJECT_SLUG}', script)
        self.assertIn('/etc/research-ops', script)
        self.assertIn('unique RESEARCH_OPS_PORT', script)

    def test_autodl_worker_uses_persistent_project_storage(self) -> None:
        script = (ROOT / "scripts" / "bootstrap_autodl.sh").read_text(encoding="utf-8")
        self.assertIn('/root/autodl-fs/${RESEARCH_OPS_PROJECT}', script)
        self.assertIn('/root/autodl-tmp/${RESEARCH_OPS_PROJECT}', script)
        self.assertIn('bootstrap_worker.sh', script)

    def test_service_file_is_rendered_per_project(self) -> None:
        service = (ROOT / "deploy" / "research-ops.service").read_text(encoding="utf-8")
        for marker in ("@PROJECT@", "@REPO_DIR@", "@ENV_FILE@", "@PYTHON@"):
            self.assertIn(marker, service)

    def test_worker_defaults_to_public_clone_and_supports_userspace_tailscale(self) -> None:
        script = (ROOT / "scripts" / "bootstrap_worker.sh").read_text(encoding="utf-8")
        self.assertIn('https://github.com/lanhung/uncertainty.git', script)
        self.assertIn('--tun=userspace-networking', script)
        self.assertIn('RESEARCH_OPS_PROJECT', script)


if __name__ == "__main__":
    unittest.main()
