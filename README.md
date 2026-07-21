# uncertainty

End-to-end, uncertainty-aware Big-Bang nucleosynthesis inference for extended
early-Universe models, with strict scientific validation and a monitored
Vultr/AutoDL execution plane.

## Scientific governance

Read these files before changing science code or launching experiments:

1. [`AGENTS.md`](AGENTS.md) — scientific mission, novelty boundaries and gates;
2. [`docs/agents/EXECUTION.md`](docs/agents/EXECUTION.md) — roles and phases;
3. [`docs/agents/COMPUTE_VALIDATION.md`](docs/agents/COMPUTE_VALIDATION.md) — compute and validation;
4. [`docs/agents/PUBLICATION.md`](docs/agents/PUBLICATION.md) — publication routes;
5. [`AGENTS-ops.md`](AGENTS-ops.md) — cluster, long-job and telemetry rules.

The high-fidelity core remains repeated BBN ODE/reaction-network solution. The
execution strategy is not blind 100-dimensional brute force: it uses competitor
reproduction, preregistration, Jacobian/Fisher screening, targeted pilots,
active learning, multi-fidelity emulation and direct-solver recovery.

## Monitored three-server topology

```text
uq-control-01  (Vultr, always on)
  Codex + authenticated status server + SQLite ledger
  live dashboard over Tailscale
  snapshots -> GitHub ops-status branch

uq-sim-01      (CPU/FP64-rich worker)
  PArthENoPE / AlterBBN / PRyMordial / LINX
  Jacobians, Fisher gate, solver labels

uq-train-01 or uq-verify-01
  emulator/flow training, MCMC, SBC and independent validation
  GPU only when benchmarked as useful
```

The task state is external to any Codex or SSH session. Workers write
heartbeats to one ledger; the dashboard and `state/SUMMARY.md` read that ledger.

## Bring up the cluster

### 1. Control node

Before running the script, make sure the control server can clone this GitHub
repository, normally through an SSH key.

```bash
git clone git@github.com:lanhung/uncertainty.git /root/uncertainty
cd /root/uncertainty
bash scripts/bootstrap_vultr.sh
```

The script installs the service, creates a root-only bearer token, creates a
separate `ops-status` branch clone, starts the server with systemd, reconciles
the plan and marks `P0-control-plane` complete.

### 2. Solver worker

```bash
git clone git@github.com:lanhung/uncertainty.git /root/uncertainty
cd /root/uncertainty
CONTROL_TAILNET_IP=<uq-control-01-tailnet-ip> \
WORKER_NAME=uq-sim-01 WORKER_ROLE=solver WORKER_INDEX=1 \
bash scripts/bootstrap_worker.sh
```

The script asks for the shared token without echoing it.

### 3. Training/validation worker

```bash
git clone git@github.com:lanhung/uncertainty.git /root/uncertainty
cd /root/uncertainty
CONTROL_TAILNET_IP=<uq-control-01-tailnet-ip> \
WORKER_NAME=uq-train-01 WORKER_ROLE=train-verify WORKER_INDEX=2 \
bash scripts/bootstrap_worker.sh
```

For AutoDL, use `scripts/bootstrap_autodl.sh`; its heartbeat/checkpoint state is
placed under `/root/autodl-fs/uncertainty-ops` by default.

Full operational instructions: [`docs/ops/CLUSTER_RUNBOOK.md`](docs/ops/CLUSTER_RUNBOOK.md).

## Daily commands

```bash
source ~/.research-ops.env             # workers
python taskctl/taskctl.py health
python taskctl/taskctl.py show
python taskctl/taskctl.py summary
python taskctl/taskctl.py reconcile    # after editing plan/plan.yaml
python taskctl/taskctl.py snapshot
```

Every long job is launched detached and wrapped:

```bash
nohup python worker/run_with_heartbeat.py \
  --task P3-pilot-1k --total 1000 --unit samples --resume \
  -- python -u scripts/data_generation/generate.py --n 1000 \
  > logs/P3-pilot-1k.log 2>&1 &
```

The child process should print `PROGRESS i/N` and optional
`METRIC key=value` lines.

## Local verification

```bash
python3 -m venv .ops-venv
source .ops-venv/bin/activate
pip install -r requirements-ops.txt
make ops-test
```

Do not upload tokens, internal meeting transcripts, unpublished raw data or
private paths to the public repository.
