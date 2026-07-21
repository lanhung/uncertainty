PYTHON ?= python3

.PHONY: ops-validate ops-test ops-server ops-show ops-reconcile ops-snapshot ops-demo

ops-validate:
	$(PYTHON) orchestrator/reconcile.py plan/plan.yaml
	$(PYTHON) -m py_compile orchestrator/*.py taskctl/*.py worker/*.py scripts/ops_demo_job.py

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
