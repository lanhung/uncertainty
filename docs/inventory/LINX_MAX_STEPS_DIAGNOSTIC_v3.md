# LINX maximum-step diagnostic v3

Status: maximum-step invariance accepted; broader convergence still open

Captured: 2026-07-22

Task: `P0-WHY-NOT-01`

## Registered question

V2 showed that the strict standard-point configuration reached LINX's default
`max_steps=4096`. V3 held `rtol=1e-8`, `atol=1e-11` and
`sampling_nTOp=2400` fixed while scanning `max_steps` over 4096, 8192, 16384
and 32768. The protocol was merged in PR #30 before execution.

The pass rule required both 16384 and 32768 to complete, each to keep the
scalar/native-batch difference below `0.01` OBS-v1 standard deviations, and
their scalar and batch abundances to agree within `0.001` OBS-v1 standard
deviations.

## Result

| `max_steps` | Outcome | Maximum scalar/batch difference |
|---:|---|---:|
| 4096 | expected structured failure | not available |
| 8192 | completed | `0.000149 sigma_obs` |
| 16384 | completed | `0.000149 sigma_obs` |
| 32768 | completed | `0.000149 sigma_obs` |

The 16384 and 32768 scalar abundances were identical to machine precision, as
were their native-batch abundances. The registered invariance difference was
therefore exactly zero. Repeat drift and within-batch spread were also zero.

The maximum-step diagnostic passes. `max_steps=16384` is retained as the
conservative follow-up value; the fact that 8192 also completed does not change
the pre-registered 16384/32768 acceptance pair.

## Runtime and failure accounting

The 4096 control retained the same explicit Diffrax maximum-step exception as
V2. Because the common runner returns nonzero when any registered case fails,
the overall process exited with code 2 even though the diagnostic's expected-
failure-aware decision passed. The host-level lease was released normally.

The run used 384.591 seconds wall time, 601.212 CPU seconds, peak RSS of
2,521,878,528 bytes, no GPU time and an estimated CNY 0.308.

## Remaining gate

V3 does not retroactively pass V1 or V2. The tolerance and weak-rate sampling
plateaus must be rerun with `max_steps=16384`; only that follow-up can nominate a
standard-point production numerical configuration. Gradient finiteness,
posterior recovery, extension coverage and cross-solver fidelity remain open.

That V4 rerun subsequently passed both unchanged plateau criteria and nominated
the strict standard-point numerical candidate. See
`docs/inventory/LINX_CONVERGENCE_RERUN_v4.md`.
