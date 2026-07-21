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

## Correct hybrid topology

The project does **not** reserve three permanent Vultr machines. It uses one
lightweight, always-on Vultr control host and two stronger, replaceable AutoDL
workers that are started only when scientific work is queued.

```text
shared Vultr control host: research-control-01
  multiple Codex processes / multiple research projects

  uncertainty instance on port 8787
    research-ops-uncertainty.service
    /etc/research-ops/uncertainty.env
    /var/lib/research-ops/uncertainty/state.db
    /root/uncertainty-status -> ops-status branch

  other-project instance on another port
    separate service, token, database and status clone

AutoDL worker: uncertainty-sim-autodl-*
  on demand; CPU/RAM/FP64 priority
  PArthENoPE / AlterBBN / PRyMordial / LINX
  Jacobians, Fisher gate, solver labels and data generation
  persistent state under /root/autodl-fs/uncertainty

AutoDL worker: uncertainty-train-autodl-*
  on demand; GPU selected by measured workload
  emulator/flow training, MCMC, SBC and independent validation
  persistent state under /root/autodl-fs/uncertainty
```

The Vultr host is a control-plane **host**, not a project-dedicated compute
node. Each project runs an isolated research-ops instance with its own project
slug, TCP port, systemd service, bearer token, SQLite directory and status
branch clone. The uncertainty instance must not collide with other Codex-managed
projects on the same machine.

The task state is external to every Codex and SSH session. AutoDL workers write
heartbeats to the uncertainty ledger; the dashboard and `state/SUMMARY.md` read
that ledger. Shutting down an AutoDL instance does not erase the plan or project
status, and checkpoints must remain on AutoDL persistent storage.

## Bring up the uncertainty control instance on shared Vultr

The Vultr host needs GitHub write access because it publishes the `ops-status`
branch. Assign a unique port for every project; this project uses 8787 by
default.

```bash
git clone git@github.com:lanhung/uncertainty.git /root/uncertainty
cd /root/uncertainty

RESEARCH_OPS_PROJECT=uncertainty \
RESEARCH_OPS_PORT=8787 \
TAILSCALE_HOSTNAME=research-control-01 \
bash scripts/bootstrap_vultr.sh
```

The script creates:

```text
research-ops-uncertainty.service
/etc/research-ops/uncertainty.env
/var/lib/research-ops/uncertainty/
/root/uncertainty-status/
```

It does not prevent the same Vultr host from running another project, provided
that project uses a different slug, port, service, state directory and status
clone.

Inspect this project instance:

```bash
systemctl status research-ops-uncertainty --no-pager
journalctl -u research-ops-uncertainty -n 100 --no-pager
set -a; source /etc/research-ops/uncertainty.env; set +a
cd /root/uncertainty
python taskctl/taskctl.py health
python taskctl/taskctl.py show
```

## Start the AutoDL solver worker

Create an AutoDL instance selected primarily for vCPU, RAM, local SSD and FP64
behavior. A GPU may be attached because of the platform allocation model, but
the solver role is not automatically a GPU workload.

```bash
git clone https://github.com/lanhung/uncertainty.git /root/uncertainty
cd /root/uncertainty

CONTROL_TAILNET_IP=<shared-vultr-tailnet-ip> \
RESEARCH_OPS_PORT=8787 \
WORKER_NAME=uncertainty-sim-autodl-01 \
WORKER_ROLE=solver \
WORKER_INDEX=1 \
bash scripts/bootstrap_autodl.sh
```

The script asks for the uncertainty control token without echoing it. Runtime
state, outbox entries and checkpoints are stored under
`/root/autodl-fs/uncertainty`; scratch I/O belongs under
`/root/autodl-tmp/uncertainty`.

## Start the AutoDL training/validation worker

Choose a 4090-class node for ordinary training and only move to A100 when
profiling shows that FP64 JAX/LINX, NUTS or memory pressure justifies it.

```bash
git clone https://github.com/lanhung/uncertainty.git /root/uncertainty
cd /root/uncertainty

CONTROL_TAILNET_IP=<shared-vultr-tailnet-ip> \
RESEARCH_OPS_PORT=8787 \
WORKER_NAME=uncertainty-train-autodl-01 \
WORKER_ROLE=train-verify \
WORKER_INDEX=2 \
bash scripts/bootstrap_autodl.sh
```

AutoDL/container environments without `/dev/net/tun` automatically use
Tailscale userspace networking. For short-lived workers, use an ephemeral,
tagged Tailscale auth key rather than copying a long-lived device identity.

Full operational instructions:
[`docs/ops/CLUSTER_RUNBOOK.md`](docs/ops/CLUSTER_RUNBOOK.md).

## AutoDL lifecycle rule

The normal lifecycle is:

```text
queued task
-> start suitable AutoDL instance
-> bootstrap/reconnect worker
-> run detached checkpointed task
-> synchronize manifests/checkpoints/artifacts
-> mark task done, blocked or safely resumable
-> shut down the AutoDL instance
```

The Vultr control instance remains available throughout. `sim` and `train` are
logical roles and may be resized, replaced or temporarily combined after a
measured cost decision; they are not permanent servers.

## Daily commands

```bash
source /root/autodl-fs/uncertainty/ops/research-ops.env  # AutoDL workers
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

Do not upload tokens, Tailscale auth keys, internal meeting transcripts,
unpublished raw data or private paths to the public repository.
