# ETR25 R0 rate-PDF audit v1

Status: **descriptive audit complete; production prohibited**

Task: `UQ0-RATE-PDF-AUDIT`

Registered: 2026-07-23

## Question and evidence limit

For each R0 reaction, this audit measures how the published actual pointwise
percentiles differ from the ETR25 scalar lognormal approximation. It does not
reconstruct the unpublished full PDF or any joint rate-curve posterior.

Let `L`, `M`, `H` and `F` denote the published actual `p16`, `p50`, `p84` and
factor uncertainty. The signed log-widths are

```text
w_lower = ln(M/L)
w_upper = ln(H/M)
sigma   = ln(F)
```

The ETR25 68% proxy endpoints are `M/F` and `M*F`. They are the registered
source convention for this comparison; they are not the exact mathematical
Normal `p16/p84` endpoints, whose z scores differ slightly from `+/-1`.

The lower endpoint residual is `ln[(M/F)/L]`; the upper endpoint residual is
`ln[(M*F)/H]`. Positive lower residual means that the actual lower percentile
extends farther down than the proxy. Negative upper residual means that the
actual upper percentile extends farther up than the proxy.

Two complementary diagnostics are retained:

```text
scale mismatch = 0.5 * (w_lower + w_upper) - sigma
log asymmetry  = w_upper - w_lower = ln(H*L/M^2)
```

Absolute log asymmetry is reported together with normalized asymmetry because
normalization can look large when the total rate width is small.

## Temperature strata

The full 60-point `T9=0.001–10` table is always audited. The primary
descriptive stratum is `T9=0.06–2.0`, containing 28 exact ETR25 knots. It is
the intersection of:

- the nuclear-network temperature domains of the accepted LINX, PRyMordial
  and PRIMAT paths; and
- the region in which all three R0 ETR25 tables retain their original
  Bayesian-rate lineage rather than the matched/adopted high-temperature
  values.

The source revisions are LINX
`ec2e9d2ca455e8204137e884da29f5dd13a638fa`, PRyMordial
`725d8a8db3ad5ea2630580d825c9d0d69ed76533`, and PRIMAT
`21ff8f39fa18e3937e9fdf386cfa982361bfdfce`.

This is an **audit coverage stratum**, not a measured physical sensitivity
window. Establishing an impact window requires localized coherent rate
perturbations, detailed-balance reverse rates, final-abundance response
weights, a preregistered cumulative-response cutoff, and a second-solver
boundary replication.

`T9=2.5–10` is reported separately: both `d+d` tables are matched/adopted from
2.5 GK and the `d(p,gamma)3He` table is matched/adopted from 5 GK.

## Quantitative result

Within the primary 28-knot stratum:

| Reaction | Maximum absolute endpoint relative error | Rows distinguishable from proxy after public-table rounding | Maximum absolute log asymmetry |
|---|---:|---:|---:|
| `d(d,n)3He` | 0.0994% | 12/28 | 0.001938 |
| `d(d,p)3H` | 0.1784% | 25/28 | 0.002574 |
| `d(p,gamma)3He` | 0.1163% | 4/28 | 0.001391 |

The source tables print four significant digits. The audit propagates
`+/-0.5` of the last printed decimal unit for every `L/M/H/F` value. Across
the full 60-knot tables, the lower/upper endpoint identities are
distinguishable from zero at reported precision for:

| Reaction | Lower | Upper | Either |
|---|---:|---:|---:|
| `d(d,n)3He` | 0/60 | 22/60 | 22/60 |
| `d(d,p)3H` | 1/60 | 48/60 | 48/60 |
| `d(p,gamma)3He` | 9/60 | 18/60 | 22/60 |

“Not distinguishable at reported precision” is not proof that the identity is
exact. Even simultaneous endpoint agreement would not establish a full
lognormal density, its tails, modes, moments, cross-temperature covariance or
cross-reaction correlations.

## Coherent-curve result and decision

The scalar proxy

```text
rate_j(T,q_j) = M_j(T) * exp[q_j * ln(F_j(T))]
```

is coherent by construction when one `q_j` is held fixed over temperature.
The deterministic probes `q=(-3,-1,0,1,3)` reconstruct `q` to at worst
`1.60e-14`. This validates the proxy implementation identity only. Actual
posterior coherence is not evaluable from public pointwise quantiles, and
independent noise per temperature bin remains prohibited.

The scalar lognormal model is therefore accepted only as an explicit
comparator. It is not declared equivalent to the actual PDF, cannot supply
actual posterior draws, does not authorize cross-reaction independence, and
does not unlock scientific label generation or the production adapter.

The coherent scientific prior, reverse-rate handling, missing-correlation
stress model and independent nuclear-data review remain work for
`UQ0-R0-RATE-PRIOR`.
