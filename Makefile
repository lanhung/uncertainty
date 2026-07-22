PYTHON ?= python3
INVENTORY ?= deploy/hosts.local.env
DIST_DIR ?= dist
UV_CACHE_DIR ?= /tmp/uncertainty-uv-cache
UV_PYTHON_INSTALL_DIR ?= /tmp/uncertainty-uv-python

.PHONY: help smoke reproduce-mini lock-check ops-validate ops-test ops-server ops-show ops-reconcile ops-snapshot ops-demo ops-local-bundle

help:
	@echo 'Primary targets:'
	@echo '  smoke          Validate repository metadata and run local unit tests'
	@echo '  reproduce-mini Verify the pinned legacy BBNet audit bundle (not a physics reproduction)'
	@echo '  lock-check     Confirm every uv lock is current without changing it'
	@echo '  ops-test       Run control-plane validation and unit tests'

smoke: lock-check ops-test reproduce-mini
	$(PYTHON) -m pytest -q tests/unit

reproduce-mini:
	$(PYTHON) -m pytest -q tests/unit/test_bbnet_legacy_inventory.py
	@echo 'AUDIT ONLY: upstream BBNet has no usable checkpoint/dataset; no abundance result is reproduced.'

lock-check:
	UV_CACHE_DIR=$(UV_CACHE_DIR) UV_PYTHON_INSTALL_DIR=$(UV_PYTHON_INSTALL_DIR) uv lock --check
	UV_CACHE_DIR=$(UV_CACHE_DIR) UV_PYTHON_INSTALL_DIR=$(UV_PYTHON_INSTALL_DIR) uv lock --project environments/solver-cpu --check
	UV_CACHE_DIR=$(UV_CACHE_DIR) UV_PYTHON_INSTALL_DIR=$(UV_PYTHON_INSTALL_DIR) uv lock --project environments/train-gpu --check
	UV_CACHE_DIR=$(UV_CACHE_DIR) UV_PYTHON_INSTALL_DIR=$(UV_PYTHON_INSTALL_DIR) uv lock --project environments/linx-v0.1.2 --check
	UV_CACHE_DIR=$(UV_CACHE_DIR) UV_PYTHON_INSTALL_DIR=$(UV_PYTHON_INSTALL_DIR) uv lock --project environments/abcmb-v0.3.1 --check

ops-validate:
	$(PYTHON) orchestrator/reconcile.py plan/plan.yaml
	$(PYTHON) -m py_compile orchestrator/*.py taskctl/*.py worker/*.py scripts/*.py

ops-test: ops-validate
	$(PYTHON) -m unittest discover -s tests/ops -v

ops-server:
	$(PYTHON) orchestrator/status_server.py

ops-show:
	$(PYTHON) taskctl/taskctl.py show

ops-reconcile:
	$(PYTHON) taskctl/taskctl.py reconcile

ops-snapshot:
	$(PYTHON) taskctl/taskctl.py snapshot

ops-demo:
	$(PYTHON) worker/run_with_heartbeat.py --task P0-ops-e2e --total 4 --unit checks -- $(PYTHON) -u scripts/ops_demo_job.py --steps 4

ops-local-bundle:
	$(PYTHON) scripts/render_local_topology_bundle.py \
		--inventory $(INVENTORY) \
		--output-dir $(DIST_DIR)/uncertainty-local-topology \
		--archive $(DIST_DIR)/uncertainty_local_topology_bundle.zip \
		--force
