# LINX extended convergence scan v2

Status: complete with structured failures; numerical consistency not accepted

Captured: 2026-07-22

Task: `P0-WHY-NOT-01`

## Purpose

V1 showed that the registered LINX scalar/native-batch difference was small,
but neither abundance-solver tolerance nor weak-rate interpolation had reached
the pre-registered plateau. V2 kept the same `0.001` OBS-v1 sigma plateau limit
and separated the two axes. Its protocol was merged in PR #28 before execution.

## Result

Only one of six registered cases completed:

| Case | Outcome | Maximum scalar/batch difference |
|---|---|---:|
| `rtol=1e-7`, `atol=1e-10`, 2400 weak-rate points | completed | `0.001374 sigma_obs` |
| `rtol=3e-8`, `atol=3e-11`, 2400 points | failed | not available |
| `rtol=1e-8`, `atol=1e-11`, 2400 points | failed | not available |
| `rtol=1e-8`, `atol=1e-11`, 300 points | failed | not available |
| `rtol=1e-8`, `atol=1e-11`, 600 points | failed | not available |
| `rtol=1e-8`, `atol=1e-11`, 1200 points | failed | not available |

All five failures have the same explicit Diffrax/Equinox cause: the abundance
ODE reached LINX's default `max_steps=4096`. The adapter preserved each
traceback in `failures.jsonl`; no failed point was clipped, retried with altered
settings, or represented as an abundance value.

The production candidate and both plateau endpoints therefore did not complete.
`numerical_consistency_status` remains `not_accepted`; the plateau values are
null rather than imputed.

## Operational record

The run exited with code 2 as designed for structured case failures and released
the `cpu-heavy` lease normally. It used 260.374 seconds wall time, 368.278 CPU
seconds, peak RSS of 2,657,038,336 bytes, no GPU time and an estimated CNY 0.208.

## Required next diagnostic

Increasing `max_steps` may be appropriate, but it changes a numerical solver
control and must be audited explicitly. The next protocol must:

1. freeze a small `max_steps` ladder before execution;
2. distinguish “enough steps to finish” from a tolerance convergence plateau;
3. record runtime and step-limit failures for scalar and native-batch paths;
4. retain the existing `0.001 sigma_obs` plateau criterion;
5. avoid promoting any configuration until an independent solver-fidelity audit.

## Scientific boundary

This is a numerical configuration failure at one standard-BBN point, not a
claim that LINX physics is wrong. It does show that the default-step direct
stack cannot support the proposed tight-tolerance production candidate. The
earlier non-finite gradient, posterior recovery, rate derivatives and extension
coverage remain separate unresolved gates.
