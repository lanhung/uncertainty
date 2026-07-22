# WHY-NOT ABCMB bundled-LINX standard-fiducial runtime v1

Status: component runtime and standard-point numerical consistency accepted; full joint pipeline pending

Captured: 2026-07-22

Task: `P0-WHY-NOT-01`

## Result

The exact W3 ABCMB source at
`5eabbab4ed7e53f264e16024743d1ba517845c37`, with bundled LINX tree
`59b3ab7b3ada7d7ff6484920e0e29291cf4a084e`, was run on
`autodl-westb-01`. The frozen adapter used JAX 0.8.1 in FP64 CPU mode, the
`key_PRIMAT_2023` network and the registered background and abundance
numerics. The input point was `Omega_b h2 = 0.02237`, `Delta N_eff = 0`, and
`tau_n = 878.3 s`.

The component timing slice completed with no structured failures:

| Measurement | Result |
|---|---:|
| cold package import | 10.464 s |
| cold first solve | 12.866 s |
| native batch compile and first solve | 19.613 s |
| 30 warm scalar solves, median | 0.31112 s/point |
| warm scalar p95 | 0.32309 s/point |
| 30 native 64-point workloads, median | 0.89676 s/batch |
| native 64-point median | 0.01401 s/point |
| timed warm points | 1,950 |
| structured failures | 0 |
| peak resident memory | 1,442,070,528 bytes |
| measured wall time | 93.245 s |
| estimated worker cost at the registered node price | CNY 0.075 |

The scalar call returned `Y_P(BBN) = 0.2468898255`, `D/H =
2.4422658302e-5`, and `N_eff = 3.0443606112`. These values are retained as
solver outputs, not as a goodness-of-fit or solver-acceptance claim.

## Numerical consistency follow-up

The native batch result was not identical to the scalar result at the same
input. The maximum absolute difference was `1.5777656725834976e-6`, dominated
by `Y_p`; the D/H difference was `8.059204979803461e-10`. The integrity
validator confirms that all expected records exist and that the summaries are
reproducible, but it does not make this difference scientifically acceptable.
The preregistered eight-case follow-up completed as
`run-20260722T113106Z`. Its candidate scalar/batch budget passed, but its
tolerance and weak-rate sampling plateaus failed the frozen `0.001 sigma`
limit. The path therefore remained numerically unaccepted for gradients,
Fisher calculations or posterior claims until an extended convergence
protocol ran. That protocol was frozen as
`configs/benchmarks/abcmb_linx_extended_convergence_v2.yaml`; it preserved the
failed V1 limits. Its six-case run `run-20260722T134322Z` completed with zero
failures. The tolerance plateau was `0.000387133 sigma` and the weak-rate
sampling plateau was `0.000771123 sigma`, both below the unchanged
`0.001 sigma` limit; candidate scalar/native-batch differences and both
zero-drift checks also passed. This accepts only the standard-point bundled-
LINX numerical candidate, not gradients, Fisher calculations or posteriors.

## Scientific boundary

This run exercised only ABCMB's bundled LINX BBN component. It did not exercise
CMB spectra, the Fisher matrix, gradient stability, HMC/NUTS, matched posterior
recovery, non-standard expansion or extension-development cost. Old likelihood
assets are unavailable, so `posterior_metrics.json` records `not_run`.

The result cannot answer the full “why not ABCMB+LINX?” question.
`P0-WHY-NOT-01` remains open and the overall conclusion remains undetermined.
