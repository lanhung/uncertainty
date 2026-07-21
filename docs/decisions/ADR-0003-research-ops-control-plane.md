# ADR-0003: External task ledger and monitored three-node control plane

- **Status:** Accepted
- **Date:** 2026-07-21
- **Scope:** all long-running experiments, Vultr/AutoDL/HPC execution, Codex operations

## Context

Research progress previously lived inside SSH and Codex sessions. This required
frequent manual polling, made ETA unverifiable, hid dead workers and allowed
long jobs to depend on an attached terminal. The scientific plan also requires
many solver shards, MCMC chains, SBC repetitions and independent validations,
so session-local tracking would become a project bottleneck.

## Decision

Adopt a four-part operations layer:

1. an always-on Vultr control node running an authenticated FastAPI service;
2. a single-writer, thread-safe SQLite task ledger reconciled from
   `plan/plan.yaml`;
3. stdlib-only `taskctl` and `run_with_heartbeat.py` clients on workers;
4. generated snapshots on an isolated `ops-status` Git branch and a live/static
   telemetry dashboard.

Every task longer than 60 seconds is detached, checkpointed and wrapped. Worker
events carry idempotency IDs and run IDs; stale attempts cannot overwrite a new
attempt. Network failures are buffered, while permanent API errors stop an
expensive command before launch.

## Alternatives rejected

- **Keep progress in Codex/tmux sessions:** not durable or independently visible.
- **Workers commit status directly to Git:** creates merge races and multiple writers.
- **Write snapshots to `main` every three minutes:** pollutes scientific history and
  conflicts with active code changes.
- **Use a hosted workflow engine immediately:** adds operational dependencies before
  the science code and workload shape are known.
- **Expose the write API without a token because Tailscale is private:** unnecessary
  defense-in-depth loss and dangerous if port 8787 is later exposed.

## Consequences

Positive:

- one URL answers what is running, stale, blocked, failed and complete;
- measured ETA comes from observed throughput;
- plans can change without erasing runtime progress;
- GitHub and LLMs receive structured summaries rather than screenshots;
- three-node operation can later extend to AutoDL/HPC without replacing the protocol.

Costs and risks:

- the control node and SQLite database require backup;
- public GitHub Pages can leak task messages if operators put sensitive content in them;
- a shared bearer token must be rotated if compromised;
- the ledger reports execution progress, not scientific validity.

## Review triggers

Revisit this ADR when any of the following occurs:

- more than roughly 20 simultaneous workers or sustained high-frequency events;
- need for per-user authorization rather than a shared token;
- multi-project orchestration on one control plane;
- requirement for event streaming, queue scheduling or automatic resource provisioning;
- SQLite or Git snapshot performance becomes a measured bottleneck.
