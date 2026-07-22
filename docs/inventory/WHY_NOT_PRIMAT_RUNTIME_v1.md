# WHY-NOT PRIMAT standard-fiducial runtime v1

Status: registered runtime slice complete; posterior and extension comparisons pending

Captured: 2026-07-22

Task: `P0-WHY-NOT-01`

## Result

The exact W2 PRIMAT source at
`21ff8f39fa18e3937e9fdf386cfa982361bfdfce` was run through its compiled C
backend on `autodl-westb-01`. The input point came from the frozen
standard-BBN subset in `configs/physics/parameter_schema.yaml`: `Omega_b h^2 =
0.02237`, `Delta N_eff = 0`, `tau_n = 878.3 s`, with all extension coordinates
at their standard-model null.

The registered timing slice completed with no failures:

| Measurement | Result |
|---|---:|
| cold package import | 0.503 s |
| cold first solve | 0.179 s |
| 30 warm scalar solves, median | 0.06387 s/point |
| warm scalar p95 | 0.06564 s/point |
| 30 sequential 64-point workloads, median | 4.104 s/batch |
| sequential 64-point median | 0.06413 s/point |
| timed warm points | 1,950 |
| structured failures | 0 |
| maximum repeated-output drift | 0 |
| peak resident memory | 157,069,312 bytes |
| measured wall time | 127.219 s |
| estimated worker cost at the registered node price | CNY 0.102 |

PRIMAT returned `Y_P(BBN) = 0.2469551308` and `D/H =
2.4447361728e-5` at this point. These are solver outputs recorded for
traceability, not an observational goodness-of-fit claim.

The 64-point workload is explicitly labeled as sequential calls because this
adapter does not claim a native vectorized batch API. Every individual timing
observation is preserved in `timings.jsonl`; the empty `failures.jsonl` is also
tracked rather than inferred from a summary.

## Scientific boundary

This completes only W2's registered standard-fiducial runtime slice. It does
not complete the required 100 posterior-region points, adversarial points,
matched posterior recovery, non-standard extension comparison or workload
projection. The old likelihood assets and extension contract are unavailable,
so `posterior_metrics.json` records `not_run` instead of a fabricated result.

No throughput result removes PRIMAT from final independent validation.
`P0-WHY-NOT-01` remains open and the overall emulator-necessity conclusion
remains undetermined.
