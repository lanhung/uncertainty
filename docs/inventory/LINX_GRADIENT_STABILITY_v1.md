# LINX standard-neighborhood gradient stability v1

Status: completed negative diagnostic; active task cancelled by ADR-0006

Date: 2026-07-22

The frozen `LINX-GRADIENT-STABILITY-v1` protocol ran in the exact LINX v0.1.2
CPU/FP64 environment at source revision
`ec2e9d2ca455e8204137e884da29f5dd13a638fa`. It evaluated all 45 registered
path/point records across the fiducial point, axis points and neighborhood
corners.

The candidate is **not accepted**. All 45 records ended as structured failures,
so both the finite-forward and finite-Jacobian fractions were zero. The main
failure classes were non-finite reverse-mode derivatives, a forward-mode
incompatibility with a `custom_vjp` path, and non-finite linear-solver output.
There were no silently accepted non-finite values.

The six diagnostic-only upstream ablations each retained one non-finite
gradient coordinate, giving a finite-gradient fraction of `14/15`. As frozen in
advance, those extreme ablations do not decide the acceptance neighborhood;
the neighborhood already fails on its own records.

The run used 1,366.680 wall seconds, 0.5772 CPU-core-hours, no GPU time and an
estimated CNY 1.0933. Its 48 offline heartbeat events were replayed in order
with zero duplicates. ADR-0006 subsequently removed generic LINX gradient
debugging from active desired state, so this negative result is retained as
backlog/direct-solver evidence and is not being debugged further.

Evidence:

- `artifacts/numerical/LINX-GRADIENT-STABILITY-v1/run-20260722T195438Z/scan_results.json`;
- `run_manifest.json`, `failures.jsonl`, `timings.jsonl` and `resource_report.json`
  in the same directory;
- the replayed immutable heartbeat outbox and replay report in the same directory.

This result does not establish that LINX physics or all LINX gradients are
invalid. It rejects only the exact registered three-coordinate candidate and
does not supply posterior, rate-gradient, HMC or UQ-gate acceptance.
