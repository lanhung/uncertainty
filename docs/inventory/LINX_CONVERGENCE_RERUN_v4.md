# LINX standard-point convergence rerun v4

Status: standard-point numerical candidate accepted; broader W0 incomplete

Captured: 2026-07-22

Task: `P0-WHY-NOT-01`

## Registered execution

V4 repeated the V2 tolerance and weak-rate interpolation axes after V3 had
independently established `max_steps=16384` versus 32768 invariance. The exact
LINX source, FP64 mode, `key_PRIMAT_2023` network, standard-BBN parameters and
OBS-v1 normalization were unchanged. The protocol was merged in PR #32 before
execution.

The production candidate was frozen as:

```text
rtol = 1e-8
atol = 1e-11
sampling_nTOp = 2400
max_steps = 16384
```

## Result

All six configurations completed, producing 48 timing records and zero
structured failures. Repeat drift and the spread among identical rows within
every native batch were exactly zero.

| Check | Measured maximum | Frozen limit | Outcome |
|---|---:|---:|---|
| candidate scalar/native-batch difference | `0.000149 sigma_obs` | `0.01 sigma_obs` | pass |
| `rtol=3e-8` versus `1e-8` plateau | `0.000364 sigma_obs` | `0.001 sigma_obs` | pass |
| 1200 versus 2400 weak-rate points plateau | `0.000774 sigma_obs` | `0.001 sigma_obs` | pass |

The looser candidate endpoints also met the scalar/native-batch budget:
`0.001374 sigma_obs` at `rtol=1e-7` and `0.000260 sigma_obs` at `rtol=3e-8`.

The standard-fiducial scalar/native-batch numerical convergence gate therefore
passes. The configuration above is nominated as the W0 standard-point numerical
candidate for later cross-solver and parameter-region audits.

## Resource record

The scan used 668.412 seconds wall time, 951.078 CPU seconds, peak RSS of
2,713,718,784 bytes, no GPU time and an estimated CNY 0.535. The `cpu-heavy`
lease was released normally after exit code 0.

## Scientific boundary

This acceptance is deliberately narrow. It covers one frozen standard-BBN
point, identical-input scalar/native-batch consistency and the registered local
convergence axes. It does not accept:

- the previously non-finite LINX gradient;
- nuclear-rate nuisance derivatives;
- posterior-region or adversarial points;
- non-standard expansion implementations;
- matched posterior recovery;
- agreement with PRIMAT, PRyMordial, PArthENoPE or AlterBBN.

The WHY-NOT decision and Track B gate therefore remain open/closed respectively.
