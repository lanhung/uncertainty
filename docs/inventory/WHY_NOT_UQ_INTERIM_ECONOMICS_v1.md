# WHY-NOT UQ interim direct-runtime economics v1

Status: **interim arithmetic boundary; full UQ economics undetermined**

Task: `P0-WHY-NOT-01`

Artifact:
`artifacts/benchmarks/WHY-NOT-UQ-INTERIM-ECONOMICS-v1/package.json`

## Purpose

This memo translates the four completed standard-fiducial runtime slices into
transparent call-equivalent reference arithmetic for the active
nuclear-rate-UQ program.
It answers only what can be computed without an accepted R0 prior or
abundance-level nuisance run. It does not complete the WHY-NOT task and does
not authorize the project-owned production or UQ1 workload. Plan v5 separately
allows the upstream native-UQ calibration reproductions to run first.

All arithmetic uses the measured warm median at one standard BBN point and the
registered worker price of CNY 2.88/hour. They omit setup, I/O, failures,
checkpointing, posterior sampling, convergence, fidelity checks and scaling
losses. These numbers are neither UQ cost projections nor lower/upper bounds.

## Measured standard-point rates and 1,000-call arithmetic

| Baseline | Warm scalar | Measured 64-workload path | Scalar-path 1,000 calls | 64-workload-path 1,000 calls |
|---|---:|---:|---:|---:|
| W0 LINX | 0.21572 s/call | 0.01342 s/point, native batch | 0.0599 worker-h, CNY 0.173 | 0.00373 worker-h, CNY 0.0107 |
| W1 PRyMordial | 5.90683 s/call | 5.86027 s/point, sequential | 1.6408 worker-h, CNY 4.725 | 1.6279 worker-h, CNY 4.688 |
| W2 PRIMAT | 0.06387 s/call | 0.06413 s/point, sequential | 0.0177 worker-h, CNY 0.051 | 0.0178 worker-h, CNY 0.0513 |
| W3 ABCMB bundled LINX | 0.31112 s/call | 0.01401 s/point, native batch | 0.0864 worker-h, CNY 0.249 | 0.00389 worker-h, CNY 0.0112 |

The W0 and W3 batch measurements repeated the standard input. They also
predate the later strict standard-point numerical candidates, which were not
retimed in the original runtime slices. These batch numbers are not
measurements of varying nuclear-rate draws and cannot be used as production
UQ throughput. W3 covers only ABCMB's bundled LINX BBN component, not the CMB,
Fisher or HMC/NUTS pipeline.

For a deliberately labeled `64 x 1,000 = 64,000` arithmetic scale proxy, the
same-cost reference arithmetic on the measured 64-workload paths gives:

- W0 LINX: 0.238 worker-hours;
- W1 PRyMordial: 104.183 worker-hours;
- W2 PRIMAT: 1.140 worker-hours;
- W3 bundled LINX component: 0.249 worker-hours.

This scale is not the registered 64-point Fisher workload, a 1,000-draw direct
MC projection or a 1,000-SBC projection. It only makes the linear arithmetic
inspectable. In particular, PRIMAT's reference time does not include the
per-draw reverse/cache guard work required by the candidate prior audit.

## Decision

The completed forward slices show that a 1,000-call fixed-point experiment is
not obviously excluded by raw standard-point runtime. They do not determine
whether a direct solver is sufficient, because none measures the accepted R0
draw distribution, native abundance-level marginalization, posterior call
count, SBC, parameter-region fidelity or two-worker scaling.

Therefore:

```text
direct solver sufficient: undetermined
emulator speed necessity: undetermined
direct-first 672 worker-hour rule evaluable: no
P0-WHY-NOT-01 progress: 0/1
```

The next valid economics update must consume real `UQ0-NATIVE-UQ-REPRO` and
`UQ1-FIDUCIAL-MC-1K` measurements after the R0 prior gate opens. A fast
standard-point reference arithmetic cannot bypass that dependency.
