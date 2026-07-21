# Shared Vultr + AutoDL research-ops runbook

## 1. Purpose

This runbook brings up the operational control plane before scientific
production. The first success criterion is not a new BBN result; it is a closed
loop in which a detached AutoDL test job survives SSH logout, reports measured
progress, becomes stale when heartbeats stop, resumes from a persistent
checkpoint and publishes a durable GitHub snapshot.

## 2. Deployment model

This project uses one lightweight, always-on control **host** and two elastic
compute roles:

| Location | Instance/role | Lifecycle | Selection priority |
|---|---|---|---|
| shared Vultr | `research-ops-uncertainty` + one or more Codex processes | always on | reliability, low cost, stable disk/network |
| AutoDL | `uncertainty-sim-autodl-*` | start when solver/Fisher work is queued | vCPU, RAM, FP64 behavior, local SSD, price |
| AutoDL | `uncertainty-train-autodl-*` / `verify-*` | start when training/SBC/validation is queued | GPU/RAM/FP64 fit, price |

The Vultr machine can manage several unrelated projects. It is therefore not
named or configured as a project-exclusive compute node. Each project receives
an isolated control-plane instance on that host.

For this repository the default isolation is:

```text
project slug: uncertainty
port:         8787
service:      research-ops-uncertainty.service
env file:     /etc/research-ops/uncertainty.env
state dir:    /var/lib/research-ops/uncertainty
status clone: /root/uncertainty-status
```

A second project must use another slug and port, for example 8788. It must not
reuse the uncertainty token, SQLite directory, service or status clone.

The AutoDL workers are disposable. Their important state belongs under
`/root/autodl-fs/uncertainty`; `/root/autodl-tmp/uncertainty` is scratch.

## 3. Preconditions

### Shared Vultr host

- Ubuntu/Debian with root or sudo;
- stable disk and outbound HTTPS/SSH;
- GitHub write-capable SSH access for `lanhung/uncertainty`;
- one Tailscale device for the host;
- one free TCP port per managed project;
- server clock synchronized with NTP;
- no public firewall exposure of project dashboard ports unless deliberately
  protected by another authenticated reverse proxy.

Verify repository access:

```bash
ssh -T git@github.com
git ls-remote git@github.com:lanhung/uncertainty.git HEAD
```

### AutoDL workers

- access to `/root/autodl-fs` persistent storage;
- outbound HTTPS;
- the uncertainty control token;
- the shared Vultr Tailscale IP;
- preferably an ephemeral, tagged and pre-authorized Tailscale auth key;
- enough local scratch space for the assigned workload.

Workers only need read access to the public repository, so HTTPS clone is the
default.

## 4. Shared Vultr control-host procedure

### 4.1 Clone the project

```bash
git clone git@github.com:lanhung/uncertainty.git /root/uncertainty
cd /root/uncertainty
```

### 4.2 Allocate the uncertainty instance

Port 8787 is the default. Confirm it is not already allocated to another project.

```bash
RESEARCH_OPS_PROJECT=uncertainty \
RESEARCH_OPS_PORT=8787 \
TAILSCALE_HOSTNAME=research-control-01 \
bash scripts/bootstrap_vultr.sh
```

The script performs:

1. shared host dependencies and Tailscale setup;
2. project repository and isolated Python environment;
3. creation/clone of the `ops-status` branch in
   `/root/uncertainty-status`;
4. generation of `/etc/research-ops/uncertainty.env` with mode `0600`;
5. creation of `/var/lib/research-ops/uncertainty`;
6. installation of `research-ops-uncertainty.service`;
7. health check, plan reconciliation and initial task updates.

### 4.3 Inspect only this project instance

```bash
systemctl status research-ops-uncertainty --no-pager
journalctl -u research-ops-uncertainty -n 100 --no-pager
set -a; source /etc/research-ops/uncertainty.env; set +a
cd /root/uncertainty
python taskctl/taskctl.py health
python taskctl/taskctl.py show
```

Record the host's Tailscale IPv4:

```bash
tailscale ip -4
```

The private dashboard is:

```text
http://<shared-vultr-tailnet-ip>:8787/
```

Securely retrieve the token from `/etc/research-ops/uncertainty.env`. Do not
paste it into a command argument, chat log, issue, screenshot or Git history.

### 4.4 Multiple Codex projects on the same host

Use separate repository checkouts and separate Codex sessions, for example:

```bash
tmux new -s codex-uncertainty
cd /root/uncertainty
codex
```

Another project uses another checkout and another tmux/session. Codex processes
may share the host, but must load the correct project's `AGENTS.md`, endpoint,
port and token before changing state. Never globally export one project's token
for all shells.

## 5. AutoDL solver worker

Create an AutoDL machine when solver/Fisher/data-generation work is ready. Pick
it by vCPU, RAM, FP64 behavior, SSD and price; the attached GPU may be incidental.

```bash
git clone https://github.com/lanhung/uncertainty.git /root/uncertainty
cd /root/uncertainty
```

For non-interactive Tailscale provisioning, load an ephemeral auth key without
putting it in shell history:

```bash
read -r -s -p 'Tailscale ephemeral auth key: ' TAILSCALE_AUTHKEY; echo
export TAILSCALE_AUTHKEY
```

Bootstrap:

```bash
CONTROL_TAILNET_IP=<CONTROL_IP> \
RESEARCH_OPS_PORT=8787 \
WORKER_NAME=uncertainty-sim-autodl-01 \
WORKER_ROLE=solver \
WORKER_INDEX=1 \
bash scripts/bootstrap_autodl.sh
```

The script prompts separately for the uncertainty research-ops token and writes:

```text
/root/autodl-fs/uncertainty/ops/research-ops.env
/root/autodl-fs/uncertainty/checkpoints/
/root/autodl-fs/uncertainty/outbox/
/root/autodl-fs/uncertainty/runs/
/root/autodl-fs/uncertainty/artifacts/
```

Verify:

```bash
source /root/autodl-fs/uncertainty/ops/research-ops.env
cd /root/uncertainty
python taskctl/taskctl.py health
python taskctl/taskctl.py show
```

## 6. AutoDL training/verification worker

Create a second AutoDL machine only when its task queue justifies concurrent
training, MCMC/SBC or independent verification. A 4090-class card is the default
starting point; A100 is used only after measured FP64/JAX/NUTS or memory evidence.

```bash
git clone https://github.com/lanhung/uncertainty.git /root/uncertainty
cd /root/uncertainty

CONTROL_TAILNET_IP=<CONTROL_IP> \
RESEARCH_OPS_PORT=8787 \
WORKER_NAME=uncertainty-train-autodl-01 \
WORKER_ROLE=train-verify \
WORKER_INDEX=2 \
bash scripts/bootstrap_autodl.sh
```

The two AutoDL roles may be resized or replaced independently. Early, low-load
work may run serially on one AutoDL instance; confirmatory independence must not
be claimed when the same environment, model state or unchecked artifact is reused.

## 7. Tailscale behavior on AutoDL

`scripts/bootstrap_worker.sh` supports:

```text
TAILSCALE_MODE=auto       # default
TAILSCALE_MODE=kernel     # normal /dev/net/tun device
TAILSCALE_MODE=userspace  # container fallback using local HTTP/SOCKS proxy
TAILSCALE_MODE=skip       # only with an explicitly protected endpoint
```

In `auto`, the script uses kernel networking when an operational Tailscale
socket is available and otherwise starts userspace networking. Userspace state
and logs remain under the AutoDL persistent project directory, while the node
identity is intended to be ephemeral.

Use a tagged ephemeral auth key for short-lived workers. Never commit or persist
the auth key in the repository. The project bearer token and Tailscale auth key
are different secrets.

## 8. End-to-end telemetry acceptance test

Run on either AutoDL worker:

```bash
source /root/autodl-fs/uncertainty/ops/research-ops.env
cd /root/uncertainty
mkdir -p logs
nohup python worker/run_with_heartbeat.py \
  --task P0-ops-e2e --total 4 --unit checks --resume \
  -- python -u scripts/ops_demo_job.py --steps 4 --sleep 10 \
  > logs/P0-ops-e2e.log 2>&1 &
```

Acceptance checks:

1. task becomes `running` and shows the AutoDL worker owner;
2. progress advances from `PROGRESS` output;
3. ETA is labelled `measured`, not invented;
4. task becomes `done` and the metric is visible;
5. `taskctl snapshot` produces a commit on `ops-status`;
6. closing SSH does not stop the job;
7. shutting down the AutoDL instance after completion does not remove ledger state;
8. a resumable test can restore from `/root/autodl-fs/uncertainty`.

For stale detection, run a longer demo, terminate the wrapper process and wait
past `stale_after_s`; never run this test on a scientific production task.

## 9. AutoDL shutdown checklist

Before stopping or releasing either AutoDL machine:

```bash
source /root/autodl-fs/uncertainty/ops/research-ops.env
cd /root/uncertainty
python taskctl/taskctl.py show
sync
```

Then confirm:

- no task is falsely left `running`;
- each incomplete task has a tested checkpoint and a recorded resume command;
- logs needed for diagnosis are copied to persistent storage;
- manifests and checksums exist for completed shards;
- irreplaceable files do not exist only under `/root/autodl-tmp`;
- dashboard messages do not expose secrets or private absolute paths.

Only then shut down the AutoDL instance. The Vultr control service remains online.

## 10. GitHub Pages

Configure repository Settings → Pages:

```text
Source branch: ops-status
Folder: /docs
```

The public page contains generated task titles, messages, metrics and artifact
links. Before enabling it, confirm those fields contain no secrets, private
paths, unpublished sensitive results or collaboration-only information. The
live Tailscale URL remains the authoritative control view.

## 11. Starting scientific execution

Do not jump directly to Pilot-10k. Follow the board order:

1. migrate and reproduce existing code;
2. competitor matrix and data/neutron preregistration;
3. solver build and benchmark;
4. Track A MCMC corrections in parallel;
5. unified rate/solver adapter;
6. 64-point Jacobian/Fisher gate;
7. only under G1/G2/G3, Pilot-1k and then Pilot-10k.

A worker command must use a task ID already present in `plan/plan.yaml`. The
server rejects unknown tasks and incomplete dependencies before launching the
expensive child command.

## 12. Recovery

### Uncertainty control service down

```bash
systemctl restart research-ops-uncertainty
journalctl -u research-ops-uncertainty -n 200 --no-pager
```

SQLite state is in `/var/lib/research-ops/uncertainty`. Restore only this
project's directory before replacing its service. Other project instances on the
same Vultr host must not be stopped or overwritten.

### AutoDL worker reclaimed or disconnected

- dashboard changes `running` to derived `stale` after the configured interval;
- inspect persistent log/checkpoint/outbox directories;
- create or restart a suitable AutoDL worker;
- run the same task with `--resume`;
- the new `run_id` supersedes delayed heartbeats from the old attempt.

### Snapshot push failure

The live ledger continues to operate. Inspect `/root/uncertainty-status`, the
control host's GitHub SSH credentials and the project-specific systemd journal;
never force-push over unexplained remote changes.

### Project token compromise

1. stop `research-ops-uncertainty.service`, not every research service;
2. generate a new token in `/etc/research-ops/uncertainty.env`;
3. update the uncertainty env file on each active AutoDL worker;
4. restart this project service and workers;
5. review this project's logs and ledger for unauthorized events.
