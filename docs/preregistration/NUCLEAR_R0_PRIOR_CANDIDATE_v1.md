# Nuclear R0 prior candidate v1

Status: **numerical candidates ready; scientific prior not selected; production prohibited**

Task: `UQ0-R0-RATE-PRIOR`

Registered: 2026-07-23

## Why this is a candidate, not a freeze

The public ETR25 products contain pointwise `p16/p50/p84` curves and a scalar
factor-uncertainty approximation, but not the R0 posterior samples,
cross-temperature covariance, cross-reaction covariance or original modified
Bayesian inputs needed to reproduce the actual functional posterior.

This package therefore completes the work that can be done without inventing
missing nuclear evidence:

- a coherent ETR25 scalar-lognormal comparator;
- a coherent, asymmetric, public-quantile-matched comparator;
- the already frozen solver-legacy calibration envelope;
- exact reverse-rate source audits for LINX, PRyMordial and PRIMAT;
- a preregistered 35-matrix correlation stress suite.

None is silently promoted to the actual ETR25 posterior or a production truth.
The task remains open with zero accepted scientific-prior reactions.

## Quantile-matched asymmetric comparator

Let `a=Phi^-1(0.84)=0.9944578832097528`,
`d_minus=ln(M/L)` and `d_plus=ln(H/M)`. For one
`q_j ~ Normal(0,1)` fixed over temperature for reaction `j`:

```text
ln rate(T,q) = ln M(T) + d_minus(T) * q/a    for q < 0
ln rate(T,q) = ln M(T) + d_plus(T)  * q/a    for q >= 0
```

All 180 public rows satisfy `L<M<H`, so at fixed temperature the transform is
positive, continuous, strictly monotone and atom-free. It reconstructs the
published rounded `p16/p50/p84` to machine precision.

Its limitations are structural:

- the temperature copula is imposed rank-one comonotonicity, not inferred from
  nuclear data;
- rate curves cannot cross;
- tails outside the central percentiles are Gaussian/lognormal extrapolations;
- the density generally has a slope kink at the median;
- cross-reaction covariance remains unknown.

It is accepted only as a C0 calibration/stress comparator. Interpolation is
linear in `log(T9)` for `ln(M)`, the lower slope and the upper slope; table
extrapolation is rejected.

## Reverse-rate contract and the PRIMAT correction

The production target is

```text
reverse_i(T,draw) = K_i(T) * forward_i(T,draw)
K_i(T) = alpha_i * T9^beta_i * exp(gamma_i/T9)
```

Forward and reverse must use the same draw and rate representation. Perturb
forward knots first, interpolate, then apply detailed balance. Any floor or
cap must be derived from that same perturbed curve.

Source inspection confirms the same perturbed forward is used by LINX and
PRyMordial. It also corrects an earlier overstatement for PRIMAT v0.3.2:
PRIMAT constructs its low-temperature reverse cap once from the
median/QED-corrected forward at load time. `apply_variations()` changes the
active forward but does not rebuild that cap. The same-draw identity therefore
holds before the cap or where the cap is inactive, not unconditionally.

The frozen worker regression at PRIMAT revision
`21ff8f39fa18e3937e9fdf386cfa982361bfdfce` evaluated all three R0 reactions,
five `q` values, 28 published knots, 27 published-grid geometric midpoints,
510 PRIMAT native LT knots, 509 native-grid geometric midpoints and both LT
boundaries. It found:

- maximum unclamped detailed-balance relative residual
  `2.35e-13`;
- maximum forward/reverse log-shift residual `1.14e-13`;
- no cap clipping above the frozen `1e-13` relative detection tolerance at
  1,070 discrete actual-LT probe points
  (`0.0116045 <= T9 <= 1.276497`);
- 90 cap-active rows above the LT boundary, so the result must not be
  extrapolated to the whole `0.06 <= T9 <= 2` diagnostic grid;
- 5,760 explicit zero/subnormal exclusions for each log-identity metric; no
  excluded row is silently assigned zero residual;
- all six same-temperature consecutive-draw cases returned the old buffer
  until the private cache keys were invalidated;
- all 12 real-wrapper MT/LT cases changed to the new draw after the project
  guard invalidated both era caches.

The regression therefore passes:

```text
reverse / (K * forward) = 1
ln[reverse(z)/reverse(0)] - ln[forward(z)/forward(0)] = 0
```

at `z=(-3,-1,0,1,3)` within the measured contract. The project guard
`worker/primat_rate_draw.py` now invalidates both cache keys for both MT and LT
networks immediately after every wrapper `apply_variations()` call. The dense
probe set is not an emitted solver trajectory or a continuous-domain proof,
and the regression used PRIMAT's native `p/expsigma`, not injected ETR25
curves. Any future adapter must use the guard and remain locked until both an
actual emitted-trajectory regression and an ETR25 curve-injection regression
are frozen.

Native inverse coefficients are not byte-identical across the three solvers.
Native reproduction is consequently a pipeline comparison. A matched-engine
claim requires one canonical coefficient source injected into every path.

## Missing-correlation stress suite

The order is frozen as:

```text
[dp_gamma_he3, dd_n_he3, dd_p_t]
```

The 35 preregistered model records include:

- one identity engineering comparator;
- four `d+d`-pair correlations `rho=(-0.9,-0.5,+0.5,+0.9)`;
- three positive common modes `rho=(0.25,0.5,0.9)`;
- a 27-point partial-correlation grid with
  `u,v,w in (-0.75,0,+0.75)`.

The Vine grid center is numerically identical to `I3`; it is retained
deliberately so the identity family anchor and the complete `3x3x3` grid both
remain explicit. Thus there are 35 model IDs and 34 unique matrices.

The grid uses

```text
rho12 = u
rho13 = v
rho23 = u*v + w*sqrt((1-u^2)*(1-v^2))
```

so every registered matrix is positive definite by construction and is
verified by determinant and Cholesky factorization. Invalid matrices fail;
nearest-PSD projection is forbidden.

This is scalar Gaussian-copula sensitivity analysis, not an estimate of the
missing ETR25 covariance. Identity is not the scientific default. Every run
must record the matrix ID/hash, factorization, seed, latent epsilon, realized
`z` and rate representation.

## Remaining blockers

The scientific prior cannot be frozen until all of the following are resolved:

1. an actual/original nuclear posterior or an explicitly approved surrogate
   policy is available;
2. the PRIMAT reverse-cap and cache regressions pass;
3. solver-specific representation injection and reverse-rate tests pass;
4. A03 nuclear-data, A00 scientific and A09 independent-validation reviews are
   signed by their real reviewers.

The present package deliberately leaves `task_done_allowed=false` and
`production_adapter_unlocked=false`.
