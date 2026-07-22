# ABCMB full-component audit v1

Status: spectra stage accepted 1/4; remaining stages cancelled by ADR-0006

Date: 2026-07-22

The exact ABCMB v0.3.1 source revision
`5eabbab4ed7e53f264e16024743d1ba517845c37` and bundled LINX tree
`59b3ab7b3ada7d7ff6484920e0e29291cf4a084e` completed all five frozen CPU/FP64
spectra cases:

| Case | Scope | Cold seconds | Warm median seconds | Repeat drift |
|---|---|---:|---:|---:|
| `S0_quick_default` | table, unlensed, lmax 500 | 73.523 | 35.462 | 0 |
| `S1_table_unlensed` | table, unlensed, lmax 2500 | 64.427 | 49.673 | 0 |
| `S2_table_lensed` | table, lensed, lmax 2500 | 71.965 | 55.621 | 0 |
| `S3_linx_unlensed` | bundled LINX, unlensed, lmax 2500 | 109.410 | 51.894 | 0 |
| `S4_linx_lensed` | bundled LINX, lensed, lmax 2500 | 72.510 | 56.378 | 0 |

Every requested `ClTT`, `ClTE`, `ClEE`, `Pk`, `YHe` and `Neff` output was
finite, had the expected shape, passed the frozen negative-noise budget and
was deterministic over the three warm repetitions. The spectra stage therefore
accounts for exactly one of four registered components.

Gradient, toy-Fisher and one-dimensional synthetic recovery were not run. The
exact environment also has no registered likelihood/covariance or HMC/NUTS
sampler. The wrapper therefore emitted a truthful terminal block at 1/4 rather
than marking the full audit done. Forty offline events were replayed in order
with zero duplicates.

ADR-0006 subsequently paused the full ABCMB audit because it is outside the
active nuclear-rate UQ critical path. The spectra evidence is retained, but no
further component credit, formal Fisher credit, posterior recovery, rate
gradient, HMC/NUTS or scientific-gate claim follows.

Evidence is under
`artifacts/numerical/ABCMB-FULL-COMPONENT-AUDIT-v1/run-20260722T201836Z/`,
including five checksum-bound spectra archives, the exact run manifest,
structured results, resource report, empty failure ledger, runner log and
heartbeat replay evidence.
