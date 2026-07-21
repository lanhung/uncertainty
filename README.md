# uncertainty

End-to-end, uncertainty-aware Big-Bang nucleosynthesis inference for extended
early-Universe models, with strict scientific validation and a monitored,
project-isolated Vultr/AutoDL execution plane.

## Scientific governance

Read these files before changing science code or launching experiments:

1. [`AGENTS.md`](AGENTS.md) — scientific mission, novelty boundaries and gates;
2. [`docs/agents/EXECUTION.md`](docs/agents/EXECUTION.md) — roles and phases;
3. [`docs/agents/COMPUTE_VALIDATION.md`](docs/agents/COMPUTE_VALIDATION.md) — compute and validation;
4. [`docs/agents/PUBLICATION.md`](docs/agents/PUBLICATION.md) — publication routes;
5. [`AGENTS-ops.md`](AGENTS-ops.md) — shared-control, long-job and telemetry rules.

The high-fidelity core remains repeated BBN ODE/reaction-network solution. The
execution strategy is not blind 100-dimensional brute force: it uses competitor
reproduction, preregistration, Jacobian/Fisher screening, targeted pilots,
active learning, multi-fidelity emulation and direct-solver recovery.

## Physical deployment: one shared control host, two elastic workers

The project does **not** own three permanent servers. It uses:

```text
shared lightweight Vultr host, always on
  multiple Codex processes and multiple unrelated research projects

  uncertainty control instance
    port 8787
    research-ops-uncertainty.service
    /etc/research-ops/uncertainty.env
    /var/lib/research-ops/uncertainty/state.db
    /root/uncertainty-status -> ops-status branch

  other project control instances
    different repos, ports, tokens, services, ledgers and status clones

AutoDL worker A, billed only while running
  25-vCPU/large-RAM/GPU-class elastic execution node
  may be solver, trainer or verifier for uncertainty or another project

AutoDL worker B, billed only while running
  independently assignable; may run another project at the same time
```

`sim`, `train` and `verify` are logical roles attached to a task. They are not
permanent identities of the two AutoDL machines. Before an uncertainty task is
started, the selected physical worker must be idle or hold an explicit
cross-project resource lease.

The control host preserves the plan and observed state while AutoDL instances
are stopped, repurposed or replaced. Workers report heartbeats over Tailscale;
Vultr manages them over their provider SSH endpoints.

## Isolation on the shared Vultr host

Every project must have a unique:

- repository checkout and Codex/tmux session;
- project slug and dashboard port;
- systemd service and environment file;
- bearer token and SQLite directory;
- status branch clone;
- GitHub credential or repository-scoped deploy key.

For uncertainty, the defaults are:

```text
slug:         uncertainty
port:         8787
service:      research-ops-uncertainty.service
env:          /etc/research-ops/uncertainty.env
state:        /var/lib/research-ops/uncertainty/
status clone: /root/uncertainty-status/
```

Do not globally export this project's token in `.bashrc`. Load it only in an
uncertainty shell.

## Local host inventory and key-based SSH

Live IPs, forwarded SSH ports and aliases are deliberately not committed to the
public repository. On the Vultr host:

```bash
cp deploy/hosts.local.env.example deploy/hosts.local.env
chmod 600 deploy/hosts.local.env
$EDITOR deploy/hosts.local.env
```

Generate one distinct SSH key for each AutoDL instance and write stable aliases:

```bash
bash scripts/setup_control_autodl_ssh.sh \
  --inventory deploy/hosts.local.env
```

After checking each AutoDL host-key fingerprint through the provider console,
install the public keys interactively:

```bash
bash scripts/setup_control_autodl_ssh.sh \
  --inventory deploy/hosts.local.env --install
```

The intended trust direction is:

```text
operator laptop -> Vultr                  personal key
Vultr -> AutoDL A                         key A
Vultr -> AutoDL B                         key B
AutoDL -> Vultr                           no reverse SSH private key
AutoDL A <-> AutoDL B                     no lateral SSH trust
AutoDL -> public GitHub repository        HTTPS read-only clone
Vultr -> GitHub                           repository-scoped credential
```

Agent forwarding and `StrictHostKeyChecking=no` are prohibited.

## Bring up the uncertainty control instance

The shared Vultr host needs GitHub write access because it publishes the
`ops-status` branch. A repository-scoped deploy key is preferred over a personal
key shared across every project.

```bash
git clone git@github.com:lanhung/uncertainty.git /root/uncertainty
cd /root/uncertainty

RESEARCH_OPS_PROJECT=uncertainty \
RESEARCH_OPS_PORT=8787 \
TAILSCALE_HOSTNAME=research-control \
bash scripts/bootstrap_vultr.sh
```

Inspect only this project instance:

```bash
systemctl status research-ops-uncertainty --no-pager
journalctl -u research-ops-uncertainty -n 100 --no-pager
set -a; source /etc/research-ops/uncertainty.env; set +a
cd /root/uncertainty
python taskctl/taskctl.py health
python taskctl/taskctl.py show
```

The dashboard is exposed only on the control host's Tailscale address:

```text
http://<control-tailnet-ip>:8787/
```

## Bootstrap an AutoDL physical worker for this project

A shared AutoDL instance has two storage namespaces:

```text
/root/autodl-tmp/projects/uncertainty/repo   local, fast, replaceable checkout
/root/autodl-fs/projects/uncertainty         persistent state for that region
```

One host-level Tailscale state is shared by every project on that physical
instance:

```text
/root/autodl-fs/_research-host/tailscale
```

From an AutoDL SSH session:

```bash
mkdir -p /root/autodl-tmp/projects/uncertainty
git clone https://github.com/lanhung/uncertainty.git \
  /root/autodl-tmp/projects/uncertainty/repo
cd /root/autodl-tmp/projects/uncertainty/repo
```

Load a Tailscale auth key without putting it in shell history, or follow the
interactive Tailscale login URL:

```bash
read -r -s -p 'Tailscale auth key: ' TAILSCALE_AUTHKEY; echo
export TAILSCALE_AUTHKEY
```

Bootstrap with a stable physical node name. The role can be changed later:

```bash
CONTROL_TAILNET_IP=<control-tailnet-ip> \
RESEARCH_OPS_PORT=8787 \
AUTODL_NODE_NAME=autodl-worker-a \
AUTODL_REGION=<region> \
WORKER_ROLE=elastic \
WORKER_INDEX=1 \
bash scripts/bootstrap_autodl.sh

unset TAILSCALE_AUTHKEY
```

For the second AutoDL instance, use another stable node name and
`WORKER_INDEX=2`.

The bootstrap intentionally does **not** add the project's env to the global
`.bashrc`. Activate it explicitly:

```bash
source /root/autodl-fs/projects/uncertainty/ops/research-ops.env
cd /root/autodl-tmp/projects/uncertainty/repo
python taskctl/taskctl.py health
python taskctl/taskctl.py show
```

## Shared-node preflight and resource leases

Before assigning either AutoDL machine:

```bash
bash scripts/autodl_node_status.sh
python scripts/capture_worker_inventory.py \
  --node-name "$AUTODL_NODE_NAME" --region "$AUTODL_REGION" \
  --output /root/autodl-fs/projects/uncertainty/artifacts/worker-inventory.json
```

Exclusive work must hold a host-level lease so other projects do not silently
share the same GPU or saturate all CPUs.

GPU example:

```bash
nohup scripts/with_resource_lease.sh \
  --resource gpu0 --project uncertainty --task P4-train -- \
  python worker/run_with_heartbeat.py \
    --task P4-train --total 200 --unit epochs --resume -- \
    python -u scripts/training/train.py \
  > logs/P4-train.log 2>&1 &
```

CPU-heavy solver example:

```bash
nohup scripts/with_resource_lease.sh \
  --resource cpu-heavy --project uncertainty --task P2.5-jacobians -- \
  python worker/run_with_heartbeat.py \
    --task P2.5-jacobians --total 64 --unit points --resume -- \
    python -u scripts/validation/run_jacobians.py \
  > logs/P2.5-jacobians.log 2>&1 &
```

The example scientific child commands are placeholders until the existing
BBNet/solver source is migrated. The resource and heartbeat wrappers are the
mandatory execution pattern.

## Storage and cross-region rule

AutoDL file storage is shared only within the same region. Two workers in
different regions must not assume that `/root/autodl-fs` is the same filesystem.

Use:

- GitHub for code, small configs, manifests and checksums;
- each region's `/root/autodl-fs/projects/uncertainty` for local durable
  checkpoints;
- approved object storage/rclone for large cross-region datasets;
- `/root/autodl-tmp` for fast caches that can be regenerated.

Do not create worker-to-worker SSH keys merely to move data. Do not route large
solver datasets through the lightweight Vultr host.

## Normal lifecycle

```text
inspect shared AutoDL node and all project leases
-> assign a logical role to an available node
-> explicitly activate uncertainty env
-> acquire gpu0/cpu-heavy/io-heavy lease
-> launch detached, heartbeat-wrapped, checkpointed work
-> persist manifests/checkpoints/artifacts
-> mark task done, failed, blocked or resumable
-> release lease
-> shut down the AutoDL instance only if no other project is using it
```

The shutdown decision is node-level. The uncertainty dashboard alone is not
enough when the machine is shared.

## Daily commands

Vultr:

```bash
set -a; source /etc/research-ops/uncertainty.env; set +a
cd /root/uncertainty
python taskctl/taskctl.py health
python taskctl/taskctl.py show
python taskctl/taskctl.py summary
python taskctl/taskctl.py reconcile
python taskctl/taskctl.py snapshot
```

AutoDL:

```bash
source /root/autodl-fs/projects/uncertainty/ops/research-ops.env
cd /root/autodl-tmp/projects/uncertainty/repo
bash scripts/autodl_node_status.sh
python taskctl/taskctl.py health
python taskctl/taskctl.py show
```

## Local verification

```bash
python3 -m venv .ops-venv
source .ops-venv/bin/activate
pip install -r requirements-ops.txt
make ops-test
```

Full runbook: [`docs/ops/CLUSTER_RUNBOOK.md`](docs/ops/CLUSTER_RUNBOOK.md).

Do not upload tokens, Tailscale auth keys, SSH private keys, local endpoint
inventories, internal meeting transcripts, unpublished raw data or private paths
to the public repository.
