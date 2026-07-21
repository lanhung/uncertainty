# ADR-0003: Shared Vultr control host and elastic AutoDL execution plane

- **Status:** Accepted, revised 2026-07-21
- **Date:** 2026-07-21
- **Scope:** all long-running experiments, shared Vultr control, AutoDL/HPC execution and Codex operations

## Context

Research progress previously lived inside SSH and Codex sessions. This required
frequent manual polling, made ETA unverifiable, hid dead workers and allowed
long jobs to depend on an attached terminal. The scientific plan also requires
many solver shards, MCMC chains, SBC repetitions and independent validations,
so session-local tracking would become a project bottleneck.

The physical deployment model is asymmetric:

- one lightweight Vultr machine remains online and hosts several Codex
  processes for several unrelated research projects;
- expensive solver and training capacity is normally rented on AutoDL only when
  work is ready;
- AutoDL instances may be resized, shut down, reclaimed or recreated, while
  project state must remain durable.

The initial wording could be read as three persistent Vultr nodes. That is not
the intended architecture.

## Decision

Adopt a hybrid control/execution layer:

1. a shared, always-on Vultr **control host**;
2. one isolated research-ops instance per project on that host;
3. a single-writer, thread-safe SQLite task ledger per project, reconciled from
   that project's `plan/plan.yaml`;
4. stdlib-only `taskctl` and `run_with_heartbeat.py` clients on elastic workers;
5. generated snapshots on each project's isolated `ops-status` Git branch and a
   live/static telemetry dashboard;
6. two default uncertainty worker roles created on AutoDL as needed:
   `sim` for solver/Fisher/data generation and `train-verify` for models,
   MCMC/SBC and independent checks.

For `lanhung/uncertainty`, the default project isolation is:

```text
service:      research-ops-uncertainty.service
port:         8787
secret env:   /etc/research-ops/uncertainty.env
ledger:       /var/lib/research-ops/uncertainty/state.db
status clone: /root/uncertainty-status
```

Every other project on the same Vultr host must use a different project slug,
port, service name, token, state directory and status clone. Projects may share
the host operating system and Tailscale device, but not their ledgers or write
credentials.

Every task longer than 60 seconds is detached, checkpointed and wrapped. Worker
events carry idempotency IDs and run IDs; stale attempts cannot overwrite a new
attempt. Network failures are buffered, while permanent API errors stop an
expensive command before launch.

AutoDL workers store resumable state in `/root/autodl-fs/<project>` and treat
`/root/autodl-tmp/<project>` as scratch. The normal lifecycle is provision,
bootstrap, execute, persist, report and shut down. The Vultr control host remains
online throughout.

## Alternatives rejected

- **Keep progress in Codex/tmux sessions:** not durable or independently visible.
- **One dedicated Vultr cluster per project:** wastes money and provides weaker
  compute choices than elastic AutoDL workers.
- **Run production solver/training on the shared Vultr host:** risks starving
  other Codex projects and couples control-plane availability to science load.
- **Use one cross-project SQLite database and token immediately:** creates
  unnecessary tenancy, authorization and failure-domain complexity.
- **Workers commit status directly to Git:** creates merge races and multiple writers.
- **Write snapshots to `main` every three minutes:** pollutes scientific history
  and conflicts with active code changes.
- **Use a hosted workflow engine immediately:** adds operational dependencies
  before the science code and workload shape are known.
- **Expose the write API without a token because Tailscale is private:** removes
  defense in depth and becomes dangerous if a port is later exposed.

## Consequences

Positive:

- one inexpensive Vultr host can supervise several projects and several Codex
  processes;
- each project keeps an independent failure domain and audit trail;
- AutoDL workers can be matched to CPU, RAM, GPU, FP64 and price requirements;
- one URL per project answers what is running, stale, blocked, failed and complete;
- measured ETA comes from observed throughput;
- plans can change without erasing runtime progress;
- GitHub and LLMs receive structured summaries rather than screenshots;
- AutoDL/HPC capacity can scale without replacing the ledger protocol.

Costs and risks:

- the shared control host becomes important infrastructure and needs host-level
  monitoring and backup;
- port and service allocation must be recorded to avoid cross-project collisions;
- each project token and SQLite database must remain isolated;
- short-lived AutoDL workers require disciplined persistent checkpoints;
- public GitHub Pages can leak task messages if operators put sensitive content in them;
- the ledger reports execution progress, not scientific validity.

## Review triggers

Revisit this ADR when any of the following occurs:

- more than roughly 20 simultaneous uncertainty workers or sustained
  high-frequency events;
- need for per-user authorization rather than a project-scoped shared token;
- need for a single aggregated dashboard or scheduler across projects;
- requirement for automatic AutoDL resource provisioning or queue scheduling;
- Tailscale userspace networking is unreliable on the chosen AutoDL images;
- SQLite or Git snapshot performance becomes a measured bottleneck;
- the shared Vultr host becomes a resource or availability bottleneck.
