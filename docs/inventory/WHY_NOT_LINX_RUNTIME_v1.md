# WHY-NOT LINX standard-fiducial runtime v1

Status: standard-point numerical candidate accepted; gradients and broader W0 not accepted

Captured: 2026-07-22

Task: `P0-WHY-NOT-01`

## Result

The exact W0 LINX source at
`ec2e9d2ca455e8204137e884da29f5dd13a638fa` ran in its dedicated JAX 0.4.28
FP64 environment on `autodl-westb-01`. The standard-BBN point used
`Omega_b h^2 = 0.02237`, `Delta N_eff = 0` and `tau_n = 878.3 s`. LINX's
documented scale-factor interface mapped these to `eta_fac =
0.9977698483` and `tau_n_fac = 0.9987491471`.

| Measurement | Result |
|---|---:|
| cold package import | 1.854 s |
| cold scalar solve | 31.283 s |
| native 64-point batch compile + first solve | 54.773 s |
| 30 warm scalar solves, median | 0.21572 s/point |
| warm scalar p95 | 0.23346 s/point |
| 30 native JAX 64-point batches, median | 0.85856 s/batch |
| native batch median | 0.01342 s/point |
| timed warm points | 1,950 |
| structured runtime failures | 0 |
| peak resident memory | 1,703,165,952 bytes |
| measured wall time | 145.187 s |
| estimated worker cost | CNY 0.116 |

The scalar reference returned `Y_P = 0.2467562286` and `D/H =
2.4416533909e-5`. The identical-input native batch returned `Y_P =
0.2467525042` and `D/H = 2.4416339272e-5` for its first point.

## Open batch discrepancy

All 30 native batches completed, but scalar and `jit(vmap)` results were not
bitwise identical. The maximum absolute differences were:

| Output | Absolute difference |
|---|---:|
| `Y_P` | 3.7244e-6 |
| `D/H` | 1.9464e-10 |
| `He3/H` | 4.1085e-11 |
| `Li7/H` | 5.6413e-15 |
| `N_eff` | 0 |

These differences are small relative to the current observational errors, but
that does not establish a numerical acceptance plateau. The artifact therefore
records `batch_discrepancy_open`.

The pre-registered follow-up scan completed all eight tolerance/interpolation
cases with zero failures and deterministic repeats. Candidate scalar/batch
differences were below `0.01` OBS-v1 standard deviations, but both required
plateau checks failed: the tight/tighter tolerance change reached `0.004045`
and the 200/300-point weak-rate interpolation change reached `0.028684`
observational standard deviations, versus the frozen `0.001` limit. Numerical
consistency is therefore **not accepted**. See
`docs/inventory/LINX_BATCH_TOLERANCE_v1.md`.

The separately frozen V2 extension then tested tighter tolerances and up to
2400 weak-rate interpolation points. Only `rtol=1e-7`, `atol=1e-10` completed;
all five cases at `rtol <= 3e-8` reached LINX's default `max_steps=4096` and
failed explicitly. Neither plateau was evaluable. See
`docs/inventory/LINX_EXTENDED_CONVERGENCE_v2.md`.

The V3 maximum-step diagnostic then held the strict tolerance and 2400-point
weak-rate grid fixed. The 4096 control failed, but 8192, 16384 and 32768 all
completed. The pre-registered 16384/32768 scalar and batch invariance difference
was exactly zero, so the maximum-step diagnostic passed. This does not yet pass
the tolerance/sampling convergence gate; that grid must be rerun at
`max_steps=16384`.

V4 reran the full strict tolerance/sampling grid at `max_steps=16384`. All six
cases completed with zero failures. The tolerance plateau was `0.000364` and
the weak-rate sampling plateau was `0.000774` OBS-v1 standard deviations, both
below the frozen `0.001` limit. The standard-point numerical candidate is
therefore accepted with `rtol=1e-8`, `atol=1e-11`, `sampling_nTOp=2400` and
`max_steps=16384`. See `docs/inventory/LINX_CONVERGENCE_RERUN_v4.md`.

The earlier upstream value-and-gradient smoke also contained a `NaN` component.
Forward runtime does not override that failure. LINX is not yet an accepted
gradient/HMC baseline.

## Scientific boundary

This completes W0's standard-fiducial runtime slice only. Scalar-rate checks,
an accepted Jacobian, posterior recovery, extension implementation, total
workload projection and parameter-region numerical validation remain open.
The WHY-NOT conclusion is still undetermined.
