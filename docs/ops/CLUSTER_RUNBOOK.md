# Three-server research cluster runbook

## 1. Purpose

This runbook brings up the operational control plane before scientific
production. The first success criterion is not a new BBN result; it is a closed
loop in which a detached test job survives SSH logout, reports measured
progress, becomes stale when heartbeats stop, resumes from a checkpoint and
publishes a durable GitHub snapshot.

## 2. Node roles

| Host | Minimum role | Selection priority |
|---|---|---|
| `uq-control-01` | Codex, status server, ledger, Git snapshots | reliability, low cost, stable disk/network |
| `uq-sim-01` | solver builds, Jacobians, Fisher, data generation | vCPU, RAM, FP64 behavior, local SSD |
| `uq-train-01` / `uq-verify-01` | training, MCMC/SBC, independent checks | RAM; GPU only when required by benchmark |

A three-server cluster is an operational topology, not a commitment to three
high-end GPUs. A later AutoDL GPU worker can replace or supplement the third
node without changing the ledger protocol.

## 3. Preconditions

- Ubuntu/Debian servers with root or sudo;
- GitHub SSH access to `lanhung/uncertainty` on the control node and workers;
- a Tailscale account or reusable auth key;
- outbound HTTPS and SSH;
- server clocks synchronized with NTP;
- no public firewall exposure of port 8787 unless deliberately protected.

Verify GitHub access before bootstrap:

```bash
ssh -T git@github.com
git ls-remote git@github.com:lanhung/uncertainty.git HEAD
```

## 4. Control node procedure

```bash
git clone git@github.com:lanhung/uncertainty.git /root/uncertainty
cd /root/uncertainty
bash scripts/bootstrap_vultr.sh
```

The script performs:

1. system dependencies and Tailscale;
2. repository and ops virtual environment;
3. creation/clone of the dedicated `ops-status` branch in
   `/root/uncertainty-status`;
4. generation of `/etc/research-ops.env` with mode `0600`;
5. systemd installation and health check;
6. plan reconciliation and initial task updates.

Inspect:

```bash
systemctl status research-ops --no-pager
journalctl -u research-ops -n 100 --no-pager
set -a; source /etc/research-ops.env; set +a
cd /root/uncertainty
python taskctl/taskctl.py health
python taskctl/taskctl.py show
```

Record the Tailscale IPv4 shown by the script. Securely retrieve the token from
`/etc/research-ops.env`; do not paste it into a command argument or chat log.

## 5. Worker procedures

### Solver worker

```bash
git clone git@github.com:lanhung/uncertainty.git /root/uncertainty
cd /root/uncertainty
CONTROL_TAILNET_IP=<CONTROL_IP> \
WORKER_NAME=uq-sim-01 \
WORKER_ROLE=solver \
WORKER_INDEX=1 \
bash scripts/bootstrap_worker.sh
```

### Training/verification worker

```bash
git clone git@github.com:lanhung/uncertainty.git /root/uncertainty
cd /root/uncertainty
CONTROL_TAILNET_IP=<CONTROL_IP> \
WORKER_NAME=uq-train-01 \
WORKER_ROLE=train-verify \
WORKER_INDEX=2 \
bash scripts/bootstrap_worker.sh
```

Each script prompts for the bearer token with terminal echo disabled and writes
`~/.research-ops.env` with mode `0600`.

## 6. End-to-end telemetry acceptance test

On a worker:

```bash
source ~/.research-ops.env
cd /root/uncertainty
nohup python worker/run_with_heartbeat.py \
  --task P0-ops-e2e --total 4 --unit checks --resume \
  -- python -u scripts/ops_demo_job.py --steps 4 --sleep 10 \
  > logs/P0-ops-e2e.log 2>&1 &
```

Acceptance checks:

1. task becomes `running` and shows the correct owner;
2. progress advances from `PROGRESS` output;
3. ETA is labelled `measured`, not invented;
4. task becomes `done` and the metric is visible;
5. `taskctl snapshot` produces a commit on `ops-status`;
6. closing the SSH session does not stop the job.

For stale detection, run a longer demo, terminate the wrapper process and wait
past `stale_after_s`; do not run this test on a scientific production task.

## 7. GitHub Pages

Configure repository Settings → Pages:

```text
Source branch: ops-status
Folder: /docs
```

The public page contains generated task titles, messages, metrics and artifact
links. Before enabling it, confirm those fields contain no secrets, private
paths, unpublished sensitive results or collaboration-only information. The
live Tailscale URL remains the authoritative control view.

## 8. Starting scientific execution

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

## 9. Recovery

### Control service down

```bash
systemctl restart research-ops
journalctl -u research-ops -n 200 --no-pager
```

SQLite state is in `/var/lib/research-ops`. Restore it before replacing the
control node. Workers buffer heartbeats locally while the server is unavailable.

### Worker reclaimed or disconnected

- dashboard changes `running` to derived `stale` after 15 minutes;
- inspect the worker log and checkpoint directory;
- restart the same task with `--resume`;
- the new `run_id` supersedes delayed heartbeats from the old attempt.

### Snapshot push failure

The live ledger continues to operate. Inspect `/root/uncertainty-status`, SSH
credentials and `journalctl`; never force-push over unexplained remote changes.

### Token compromise

1. stop the service;
2. generate a new token in `/etc/research-ops.env`;
3. update each worker's `~/.research-ops.env`;
4. restart service and workers;
5. review server logs and ledger for unauthorized events.
