from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class TopologyContractTests(unittest.TestCase):
    def test_authoritative_files_do_not_restore_permanent_role_hostnames(self) -> None:
        root_agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        plan = (ROOT / "plan" / "plan.yaml").read_text(encoding="utf-8")
        authoritative_text = root_agents + "\n" + plan
        for legacy_name in (
            "uq-control-01",
            "uq-sim-01",
            "uq-train-01",
            "uq-verify-01",
        ):
            self.assertNotIn(legacy_name, authoritative_text)
        self.assertIn("ADR-0004-shared-control-elastic-autodl.md", root_agents)

    def test_vultr_control_instance_is_project_scoped(self) -> None:
        script = (ROOT / "scripts" / "bootstrap_vultr.sh").read_text(encoding="utf-8")
        self.assertIn(
            'SERVICE_NAME="${RESEARCH_OPS_SERVICE_NAME:-research-ops-${PROJECT_SLUG}}"',
            script,
        )
        self.assertIn("/var/lib/research-ops/${PROJECT_SLUG}", script)
        self.assertIn("/etc/research-ops", script)
        self.assertIn("unique RESEARCH_OPS_PORT", script)

    def test_autodl_worker_separates_project_and_host_state(self) -> None:
        script = (ROOT / "scripts" / "bootstrap_autodl.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "/root/autodl-fs/projects/${RESEARCH_OPS_PROJECT}", script
        )
        self.assertIn(
            "/root/autodl-tmp/projects/${RESEARCH_OPS_PROJECT}", script
        )
        self.assertIn(
            "/root/autodl-fs/_research-host/${AUTODL_NODE_NAME}", script
        )
        self.assertIn(
            "/root/autodl-tmp/_research-host/${AUTODL_NODE_NAME}", script
        )
        self.assertIn('AUTO_SOURCE_WORKER_ENV="${AUTO_SOURCE_WORKER_ENV:-0}"', script)
        self.assertIn("bootstrap_worker.sh", script)

    def test_service_file_is_rendered_per_project(self) -> None:
        service = (ROOT / "deploy" / "research-ops.service").read_text(
            encoding="utf-8"
        )
        for marker in ("@PROJECT@", "@REPO_DIR@", "@ENV_FILE@", "@PYTHON@"):
            self.assertIn(marker, service)

    def test_worker_defaults_to_public_clone_and_supports_userspace_tailscale(self) -> None:
        script = (ROOT / "scripts" / "bootstrap_worker.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("https://github.com/lanhung/uncertainty.git", script)
        self.assertIn("--tun=userspace-networking", script)
        self.assertIn("TAILSCALE_STATE_DIR", script)
        self.assertIn("TAILSCALE_RUNTIME_DIR", script)
        self.assertIn("RESEARCH_OPS_PROJECT", script)

    def test_shared_worker_has_resource_lease_and_key_setup_tools(self) -> None:
        lease = (ROOT / "scripts" / "with_resource_lease.sh").read_text(
            encoding="utf-8"
        )
        ssh_setup = (ROOT / "scripts" / "setup_control_autodl_ssh.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("flock", lease)
        self.assertIn("/var/lock/research-workers", lease)
        self.assertIn("one key pair per worker", ssh_setup)
        self.assertIn("WORKER_PREFIXES=(AUTODL1 AUTODL2)", ssh_setup)
        self.assertIn("WORKER_PREFIXES+=(AUTODL3)", ssh_setup)
        self.assertIn("SSH_CONTROL_PATH_DIR", ssh_setup)
        self.assertIn("StrictHostKeyChecking yes", ssh_setup)
        self.assertIn("ForwardAgent no", ssh_setup)

    def test_inventory_records_effective_container_limits(self) -> None:
        inventory = (ROOT / "scripts" / "capture_worker_inventory.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("effective_logical_cpu_count", inventory)
        self.assertIn("/sys/fs/cgroup/cpu.max", inventory)
        self.assertIn("/sys/fs/cgroup/memory.max", inventory)


if __name__ == "__main__":
    unittest.main()
