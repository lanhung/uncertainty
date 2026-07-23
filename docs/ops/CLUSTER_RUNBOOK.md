# Shared Vultr control host + elastic AutoDL worker-pool runbook

## 1. Purpose

This runbook brings up the operational control plane before scientific
production. The first success criterion is not a new BBN result. It is a closed
loop in which:

- a shared, lightweight Vultr host runs several project-isolated Codex/control
  instances;
- either of two AutoDL machines can be assigned to this project only while work
  is queued;
- a detached job survives SSH logout;
- progress and measured ETA reach the uncertainty ledger;
- checkpoint state survives AutoDL shutdown;
- another project cannot silently take the same GPU or saturate the same CPU;
- no secret or large dataset is routed through the wrong control plane.

## 2. Correct deployment model

### 2.1 Physical machines

| Physical location | Lifecycle | Responsibility |
|---|---|---|
| shared Vultr | lightweight, always on | several Codex sessions, one isolated status/ledger instance per project, GitHub operations |
| AutoDL worker A | on demand, shared across projects | solver, training or validation according to current lease |
| AutoDL worker B | on demand, shared across projects | solver, training or validation according to current lease |

The two AutoDL machines are not permanently named `sim` and `train`. Those are
logical roles selected at task launch time.

### 2.2 Uncertainty control-instance isolation

```text
project slug: uncertainty
port:         8787
service:      research-ops-uncertainty.service
env file:     /etc/research-ops/uncertainty.env
state dir:    /var/lib/research-ops/uncertainty
status clone: /root/uncertainty-status
```

A second project on the same Vultr host must use a different repo, port, token,
service, state directory and status clone. Never globally export one project's
token for all Codex shells.

### 2.3 AutoDL project and host namespaces

```text
/root/autodl-tmp/projects/uncertainty/repo
    fast, local, replaceable checkout and scratch

/root/autodl-fs/projects/uncertainty/
    region-local persistent checkpoint, outbox, manifest and artifact state

/root/autodl-fs/_research-host/tailscale/
    one physical-node Tailscale identity shared by all projects

/var/lock/research-workers/
    node-level cross-project leases such as gpu0 and cpu-heavy
```

## 3. Network and trust model

Use two separate channels:

1. **Management channel**: Vultr logs into the AutoDL forwarded SSH endpoints.
2. **Telemetry channel**: AutoDL connects outward to the Vultr Tailscale address
   and uncertainty API port 8787.

Do not expose dashboard port 8787 directly on the Vultr public interface.

Recommended SSH trust:

```text
operator laptop -> Vultr                  personal key
Vultr -> AutoDL A                         key A
Vultr -> AutoDL B                         key B
AutoDL -> Vultr                           no reverse SSH private key
AutoDL A <-> AutoDL B                     no lateral SSH trust
AutoDL -> public GitHub repository        HTTPS read-only clone
Vultr -> GitHub                           repository-scoped credential
```

Never use SSH agent forwarding, copy the Vultr private key to AutoDL, or set
`StrictHostKeyChecking=no`.

## 4. Preconditions

### 4.1 Shared Vultr host

- Ubuntu/Debian with root or sudo;
- stable disk and outbound HTTPS/SSH;
- GitHub write-capable, preferably repository-scoped SSH credential;
- one Tailscale device for the physical host;
- one free TCP port per managed project;
- NTP-synchronized clock;
- dashboard ports blocked from the public internet.

### 4.2 AutoDL workers

- access to `/root/autodl-fs` and `/root/autodl-tmp`;
- outbound HTTPS;
- provider SSH endpoint and port;
- uncertainty research-ops token;
- control host's Tailscale IP;
- Tailscale authentication or an already-running host-level Tailscale daemon;
- enough free node-level resources after checking other projects.

The AutoDL workers only need read access to this public repository, so HTTPS
clone is the default. Code changes and GitHub pushes should normally happen on
Vultr, not from workers.

## 5. Operator laptop to Vultr key-based login

Generate a dedicated personal key on the operator machine:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519_research_vultr \
  -C 'operator->research-vultr'
ssh-copy-id -i ~/.ssh/id_ed25519_research_vultr.pub root@<VULTR_PUBLIC_IP>
```

Add a local alias:

```sshconfig
Host vultr-research
  HostName <VULTR_PUBLIC_IP>
  User root
  IdentityFile ~/.ssh/id_ed25519_research_vultr
  IdentitiesOnly yes
  ForwardAgent no
  ServerAliveInterval 30
  ServerAliveCountMax 6
```

Verify key login in a second terminal before disabling password authentication.
If hardening SSH, use `PermitRootLogin prohibit-password` or migrate to a sudo
user; never lock out the only tested management path.

## 6. Shared Vultr to AutoDL key-based login

### 6.1 Create the local inventory

On the Vultr uncertainty checkout:

```bash
cd /root/uncertainty
cp deploy/hosts.local.env.example deploy/hosts.local.env
chmod 600 deploy/hosts.local.env
$EDITOR deploy/hosts.local.env
```

This local file contains the current provider endpoints, forwarded ports, stable
node names and regions. It is gitignored because endpoints are operational
inventory and can change when instances are rebuilt.

### 6.2 Generate node-specific keys and aliases

```bash
bash scripts/setup_control_autodl_ssh.sh \
  --inventory deploy/hosts.local.env
```

The script creates one private key per AutoDL instance under:

```text
/root/.ssh/research-workers/
```

It writes SSH aliases to:

```text
/root/.ssh/research-workers.conf
```

### 6.3 Verify host keys, then install public keys

Before accepting a host key, compare its fingerprint with the AutoDL instance:

On AutoDL through the provider console or an already-trusted login:

```bash
ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
```

On Vultr:

```bash
ssh-keyscan -p <PORT> <HOST> 2>/dev/null | ssh-keygen -lf -
```

Only after the fingerprints agree:

```bash
bash scripts/setup_control_autodl_ssh.sh \
  --inventory deploy/hosts.local.env --install
```

The installed public key is restricted from agent, X11 and TCP forwarding. The
shell itself remains available for commands, tmux, rsync of small files and
incident diagnosis.

Test:

```bash
ssh <AUTODL_ALIAS_A> hostname
ssh <AUTODL_ALIAS_B> hostname
```

If an AutoDL instance is rebuilt and the host key legitimately changes:

```bash
ssh-keygen -R '[<HOST>]:<PORT>'
```

Then repeat fingerprint verification. Do not suppress the warning globally.

## 7. GitHub credential isolation on shared Vultr

A repository-scoped deploy key avoids reusing one personal GitHub key for every
Codex-managed project.

Generate on Vultr:

```bash
ssh-keygen -t ed25519 -N '' \
  -f /root/.ssh/id_ed25519_github_uncertainty \
  -C 'uncertainty-control->github'
cat /root/.ssh/id_ed25519_github_uncertainty.pub
```

Add the public key under repository Settings → Deploy keys. The uncertainty
control plane needs write access because it pushes the `ops-status` branch.

Use a host alias in `/root/.ssh/config`:

```sshconfig
Host github-uncertainty
  HostName github.com
  User git
  IdentityFile /root/.ssh/id_ed25519_github_uncertainty
  IdentitiesOnly yes
  ForwardAgent no
```

Clone using:

```bash
git clone git@github-uncertainty:lanhung/uncertainty.git /root/uncertainty
```

When bootstrapping, pass the same alias explicitly:

```bash
REPO_URL=git@github-uncertainty:lanhung/uncertainty.git \
RESEARCH_OPS_PROJECT=uncertainty \
RESEARCH_OPS_PORT=8787 \
bash scripts/bootstrap_vultr.sh
```

## 8. Bring up the uncertainty control instance

```bash
cd /root/uncertainty
RESEARCH_OPS_PROJECT=uncertainty \
RESEARCH_OPS_PORT=8787 \
TAILSCALE_HOSTNAME=research-control \
bash scripts/bootstrap_vultr.sh
```

The script performs:

1. shared host dependency and Tailscale setup;
2. project-isolated virtual environment;
3. creation/clone of `ops-status` in `/root/uncertainty-status`;
4. mode-0600 `/etc/research-ops/uncertainty.env`;
5. `/var/lib/research-ops/uncertainty` state directory;
6. `research-ops-uncertainty.service` installation;
7. health check, plan reconciliation and initial status.

Inspect:

```bash
systemctl status research-ops-uncertainty --no-pager
journalctl -u research-ops-uncertainty -n 100 --no-pager
set -a; source /etc/research-ops/uncertainty.env; set +a
cd /root/uncertainty
python taskctl/taskctl.py health
python taskctl/taskctl.py show
tailscale ip -4
```

Private dashboard:

```text
http://<CONTROL_TAILNET_IP>:8787/
```

## 9. Multiple Codex projects on Vultr

Use one checkout and one tmux session per project:

```bash
tmux new -s codex-uncertainty
cd /root/uncertainty
codex
```

A different project uses a different checkout/session/port/env. Before a Codex
process changes task state, it must explicitly load this project's environment:

```bash
set -a
source /etc/research-ops/uncertainty.env
set +a
```

Do not place that source line in the shared host's global `.bashrc`.

## 10. Bootstrap either AutoDL node for uncertainty

### 10.1 Connect from Vultr

```bash
ssh <AUTODL_ALIAS>
```

A physical node can be used by other projects. First inspect it:

```bash
nvidia-smi
uptime
free -h
df -h / /root/autodl-tmp /root/autodl-fs
ps -eo pid,ppid,%cpu,%mem,etime,args --sort=-%cpu | head -40
```

If uncertainty is already cloned:

```bash
cd /root/autodl-tmp/projects/uncertainty/repo
git pull --ff-only
bash scripts/autodl_node_status.sh
```

Otherwise:

```bash
mkdir -p /root/autodl-tmp/projects/uncertainty
git clone https://github.com/lanhung/uncertainty.git \
  /root/autodl-tmp/projects/uncertainty/repo
cd /root/autodl-tmp/projects/uncertainty/repo
```

### 10.2 Tailscale authentication

The physical AutoDL node has one host-level Tailscale identity, shared by every
project. If it is not yet authenticated, either follow the interactive login URL
or load an auth key without shell-history exposure:

```bash
read -r -s -p 'Tailscale auth key: ' TAILSCALE_AUTHKEY; echo
export TAILSCALE_AUTHKEY
```

A tagged, pre-authorized key is suitable for a server. Use an ephemeral key only
when the node identity is intentionally disposable; the default script retains
host-level state under `/root/autodl-fs/_research-host/tailscale`.

### 10.3 Bootstrap the project namespace

```bash
CONTROL_TAILNET_IP=<CONTROL_TAILNET_IP> \
RESEARCH_OPS_PORT=8787 \
AUTODL_NODE_NAME=<STABLE_PHYSICAL_NODE_NAME> \
AUTODL_REGION=<REGION> \
WORKER_ROLE=elastic \
WORKER_INDEX=<1_OR_2> \
bash scripts/bootstrap_autodl.sh

unset TAILSCALE_AUTHKEY
```

The role is deliberately `elastic`. When a real task launches, record whether
this attempt is solver, train or verify work.

The bootstrap writes:

```text
/root/autodl-fs/projects/uncertainty/ops/research-ops.env
/root/autodl-fs/projects/uncertainty/checkpoints/
/root/autodl-fs/projects/uncertainty/outbox/
/root/autodl-fs/projects/uncertainty/runs/
/root/autodl-fs/projects/uncertainty/artifacts/
/root/autodl-fs/projects/uncertainty/manifests/
```

It does not append the env file to global `.bashrc` on a shared worker.

Activate explicitly:

```bash
source /root/autodl-fs/projects/uncertainty/ops/research-ops.env
cd /root/autodl-tmp/projects/uncertainty/repo
python taskctl/taskctl.py health
python taskctl/taskctl.py show
```

## 11. Capture the real AutoDL hardware before planning work

The advertised image and GPU-memory amount do not replace a benchmark. On each
node:

```bash
source /root/autodl-fs/projects/uncertainty/ops/research-ops.env
cd /root/autodl-tmp/projects/uncertainty/repo

bash scripts/autodl_node_status.sh
python scripts/capture_worker_inventory.py \
  --node-name <STABLE_PHYSICAL_NODE_NAME> \
  --region <REGION> \
  --output /root/autodl-fs/projects/uncertainty/artifacts/worker-inventory.json
```

Record:

- actual GPU name, UUID, memory and driver;
- PyTorch/CUDA compatibility;
- 25-vCPU topology rather than only the count;
- available RAM and local/persistent disk space;
- cold/warm solver runtime and FP64 behavior;
- interference from other projects.

Do not modify the base Python environment globally. Scientific dependencies
belong in a project-specific locked environment.

## 12. Cross-project resource lease

Before an exclusive workload, acquire a host-level lease.

### GPU task

```bash
source /root/autodl-fs/projects/uncertainty/ops/research-ops.env
cd /root/autodl-tmp/projects/uncertainty/repo
mkdir -p logs

nohup scripts/with_resource_lease.sh \
  --resource gpu0 --project uncertainty --task <TASK_ID> -- \
  python worker/run_with_heartbeat.py \
    --task <TASK_ID> --total <N> --unit <UNIT> --resume -- \
    <ACTUAL_COMMAND> \
  > logs/<TASK_ID>.log 2>&1 &
```

### CPU-heavy solver task

```bash
nohup scripts/with_resource_lease.sh \
  --resource cpu-heavy --project uncertainty --task <TASK_ID> -- \
  env OMP_NUM_THREADS=22 MKL_NUM_THREADS=22 \
  python worker/run_with_heartbeat.py \
    --task <TASK_ID> --total <N> --unit points --resume -- \
    <ACTUAL_SOLVER_COMMAND> \
  > logs/<TASK_ID>.log 2>&1 &
```

Exit code 75 means another project owns the resource. Do not delete its lock.
Investigate the metadata under `/var/lock/research-workers/*.json`.

Default policy:

- one project at a time on `gpu0`;
- one CPU-saturating project at a time under `cpu-heavy`;
- leave several vCPUs for the operating system, heartbeat and I/O;
- only share the GPU after an explicit profiling decision.

When a long run completes only one component of a still-active parent task,
use `--success-event progress --success-current <ABSOLUTE_COUNT>`. This emits a
nonterminal task update. Reserve the default `done` event for completion of the
whole task, and use `block` only when the remaining work is genuinely blocked.
If a component executes correctly but fails its frozen scientific acceptance
threshold, use
`--failure-event progress --failure-current <CURRENT_ACCEPTED_COUNT>` and a
specific `--failure-reason`. The child still exits nonzero for automation, but
the parent remains active instead of being falsely marked failed.

## 13. End-to-end telemetry acceptance test

On either AutoDL node:

```bash
source /root/autodl-fs/projects/uncertainty/ops/research-ops.env
cd /root/autodl-tmp/projects/uncertainty/repo
mkdir -p logs

nohup scripts/with_resource_lease.sh \
  --resource cpu-heavy --project uncertainty --task P0-ops-e2e -- \
  python worker/run_with_heartbeat.py \
    --task P0-ops-e2e --total 4 --unit checks --resume -- \
    python -u scripts/ops_demo_job.py --steps 4 --sleep 10 \
  > logs/P0-ops-e2e.log 2>&1 &
```

Acceptance checks:

1. the task becomes `running` and reports the selected physical worker;
2. progress advances from absolute `PROGRESS` output;
3. ETA is labelled `measured`, never fabricated;
4. the task becomes `done` and the metric is visible;
5. `taskctl snapshot` creates an `ops-status` commit;
6. closing SSH does not stop the job;
7. the lease metadata disappears after completion;
8. a resumable test restores from the project persistent directory;
9. stopping the AutoDL instance does not remove Vultr ledger state.

Use only a demo task for stale testing.

## 14. Storage and cross-region transfer

AutoDL file storage is shared among instances **in the same region**. Workers in
different regions must be treated as separate persistent stores.

Use:

- GitHub: code, small configs, ADRs, manifests and checksums;
- `/root/autodl-fs/projects/uncertainty`: durable state local to that region;
- `/root/autodl-tmp/projects/uncertainty`: high-I/O cache and replaceable data;
- approved S3/OSS/R2/B2/rclone data layer: large immutable cross-region shards;
- Vultr: ledger, small reports and recovery indices only.

Do not create AutoDL-to-AutoDL SSH trust merely to transfer files. Do not route
large solver datasets through Vultr. Each cross-region object must have a
checksum, immutable name, manifest, solver/config hash and origin region.

## 15. Shutdown checklist for a shared AutoDL physical node

A project can finish while another project still uses the machine. Therefore the
shutdown decision is node-level.

For uncertainty:

```bash
source /root/autodl-fs/projects/uncertainty/ops/research-ops.env
cd /root/autodl-tmp/projects/uncertainty/repo
python taskctl/taskctl.py show
bash scripts/autodl_node_status.sh
sync
```

Confirm:

- no uncertainty task is falsely `running`;
- every incomplete uncertainty task has a tested checkpoint and resume command;
- required logs, manifests and checksums are persistent;
- no irreplaceable file exists only under `/root/autodl-tmp`;
- `/var/lock/research-workers` has no lease for **any** project;
- `nvidia-smi` and process inspection show no other project's active work;
- the AutoDL provider console confirms no collaborator expects the instance.

Only then shut down or release the physical instance.

## 16. Starting scientific execution

Do not jump directly to Pilot-10k. Follow the board order:

1. migrate and reproduce existing code;
2. competitor matrix and data/neutron preregistration;
3. solver build and real hardware benchmark;
4. Track A MCMC corrections in parallel;
5. unified rate/solver adapter;
6. 64-point Jacobian/Fisher gate;
7. only under G1/G2/G3, Pilot-1k and then Pilot-10k.

A worker command must use a task ID already present in `plan/plan.yaml`. The
server rejects unknown tasks and unmet dependencies before launching expensive
work.

## 17. Recovery

### Uncertainty control service down

```bash
systemctl restart research-ops-uncertainty
journalctl -u research-ops-uncertainty -n 200 --no-pager
```

Restore only `/var/lib/research-ops/uncertainty`; do not stop or overwrite other
project services on the shared Vultr host.

### AutoDL worker rebuilt or endpoint changed

1. verify the new provider instance and SSH host fingerprint;
2. remove only the stale `[host]:port` known-host entry;
3. reinstall that node's public key;
4. clone/rebuild the uncertainty scratch checkout;
5. re-bootstrap using the same stable logical node name or a documented new one;
6. resume from persistent/object-storage checkpoint with a new `run_id`.

### Tailscale userspace daemon down

Inspect:

```text
/root/autodl-fs/_research-host/tailscale/tailscaled.log
/root/autodl-fs/_research-host/tailscale/tailscaled.pid
/root/autodl-fs/_research-host/tailscale/tailscaled.sock
```

Restart through `scripts/bootstrap_autodl.sh`; do not launch one daemon per
project on the same physical node.

### Snapshot push failure

The live ledger remains authoritative. Inspect `/root/uncertainty-status`, the
repo-scoped GitHub credential and `research-ops-uncertainty` journal. Never
force-push over unexplained remote changes.

### Token compromise

1. stop only `research-ops-uncertainty.service`;
2. rotate the token in `/etc/research-ops/uncertainty.env`;
3. replace the uncertainty env file on active AutoDL workers;
4. restart the uncertainty service;
5. review this project's ledger and logs;
6. do not rotate unrelated project tokens unless separately affected.
