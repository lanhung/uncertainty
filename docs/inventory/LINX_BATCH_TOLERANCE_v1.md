# LINX scalar/native-batch tolerance scan v1

Status: complete; numerical consistency not accepted

Captured: 2026-07-22

Task: `P0-WHY-NOT-01`

## Registered execution

The scan used the exact W0 LINX source
`ec2e9d2ca455e8204137e884da29f5dd13a638fa`, JAX 0.4.28, FP64, the
`key_PRIMAT_2023` network and the frozen standard-BBN point. The protocol was
merged before measurement in PR #26. It paired five abundance-solver tolerance
levels with three additional neutron/proton weak-rate interpolation resolutions.
Every configuration compared one scalar solve with 64 identical inputs through
native `jit(vmap)` and then repeated both paths three times.

The normalization uses frozen OBS-v1 errors: `sigma(Y_P) = 0.0013` and
`sigma(D/H) = 3e-7` in raw abundance units.

## Result

All eight configurations completed. The artifact contains 64 timing records,
zero structured failures, zero repeat drift and zero spread among identical
rows within any native batch.

| Case | `rtol` | `atol` | weak-rate points | max scalar/batch difference in OBS sigma |
|---|---:|---:|---:|---:|
| loose | `1e-5` | `1e-8` | 150 | 0.024770 |
| intermediate | `3e-6` | `3e-9` | 150 | 0.005247 |
| registered | `1e-6` | `1e-9` | 150 | 0.002865 |
| tight | `3e-7` | `3e-10` | 150 | 0.001504 |
| tighter | `1e-7` | `1e-10` | 150 | 0.000134 |
| sampling 100 | `1e-6` | `1e-9` | 100 | 0.001290 |
| sampling 200 | `1e-6` | `1e-9` | 200 | 0.003294 |
| sampling 300 | `1e-6` | `1e-9` | 300 | 0.001661 |

The three production-candidate tolerance cases individually satisfy the
pre-registered scalar/batch budget of `0.01` observational standard deviations.
That condition alone is insufficient for acceptance.

## Failed plateau checks

The tightened-tolerance comparison between `3e-7/3e-10` and `1e-7/1e-10`
changed the scalar or batch result by as much as `0.004045` observational
standard deviations. The pre-registered plateau limit was `0.001`.

The weak-rate interpolation comparison between 200 and 300 points changed the
result by as much as `0.028684` observational standard deviations, also above
the `0.001` limit. The effect is deterministic rather than stochastic: repeat
drift and within-batch spread were exactly zero.

Therefore `numerical_consistency_status = not_accepted`. The registered
`rtol=1e-6`, `atol=1e-9`, `sampling_nTOp=150` configuration may support the
reported runtime measurement, but it is not promoted to a production-fidelity
configuration. A separately frozen extended convergence scan is required.

## Resource record

The scan used 719.823 seconds wall time, 780.540 CPU seconds, peak RSS of
1,965,047,808 bytes and no GPU time. At the registered worker price, its
estimated cost was CNY 0.576. The host-level `cpu-heavy` lease was released
normally after exit code 0.

## Scientific boundary

This negative gate concerns only scalar/native-batch consistency at one frozen
standard-BBN point. It neither validates nor invalidates LINX physics relative
to another solver. The earlier non-finite gradient remains rejected, and rate
nuisance derivatives, posterior recovery and non-standard expansion remain
unmeasured.
