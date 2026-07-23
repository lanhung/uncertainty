# ETR25 R0 public-product ingest v1

Status: **public products captured; descriptive rate-PDF audit complete; production prohibited**

Task: `UQ0-ETR25-R0-INGEST`

Registered: 2026-07-23

## Scope

This record pins the public ETR25 products for the three R0 deuterium
reactions:

| Reaction | ETR25 table | Public numerical product |
|---|---:|---|
| `D(p,gamma)3He` | 6 | IOP publisher ASCII, 60 `T9` knots |
| `D(d,n)3He` | 7 | IOP publisher ASCII, 60 `T9` knots |
| `D(d,p)3H` | 8 | IOP publisher ASCII, 60 `T9` knots |

The exact URLs, byte lengths and SHA256 values are frozen in
`configs/physics/etr25_R0_ingest_v1.yaml`. The derived package uses the
official IOP ASCII bytes as its primary source and requires an exact numerical
and parenthesis-flag match to `paper.tex` from pinned arXiv source
`2601.20059v1`.

Attribution: Tables 6–8 are from Iliadis et al., *The 2025 Evaluation of
Experimental Thermonuclear Reaction Rates*, ApJS 283, 17 (2026),
doi:10.3847/1538-4365/ae2bdc, licensed CC BY 4.0. The package changes the
publisher's two-column layout into one sorted grid and records parentheses as
`high_temperature_matched_rate`.

## Frozen semantics

`Low`, `Median` and `High` are the 16th, 50th and 84th percentiles of the
actual pointwise rate probability density. `f.u.` is a separate log-normal
approximation with `sigma_ln = ln(f.u.)`. These are not interchangeable data
products.

The ETR25 scalar network approximation is permitted only as a named baseline:

```text
rate_j(T) = median_j(T) * f.u._j(T)^p_j
p_j ~ Normal(0, 1)
```

One `p_j` is held fixed over temperature within a network realization. This is
a coherent scalar log-normal curve, not a draw from the unpublished actual
functional posterior.

Parenthesized high-temperature values start at `T9=5` for
`D(p,gamma)3He` and at `T9=2.5` for both `D(d,*)` rates. Their lineage is Coc
et al. (2015), so they are not labeled as a continuous extension of the
lower-temperature Bayesian calculation.

## Negative availability result

The audited ETR25 GitHub repository, Zenodo record `10.5281/zenodo.17610211`
and publisher products do not contain the three R0 Bayesian model inputs,
posterior samples, actual rate-curve draws, cross-temperature covariance or
cross-reaction covariance. The Zenodo input/output archives cover 69
non-Bayesian rates; the R0 rates are documented exceptions.

Consequently:

- pointwise percentiles cannot be independently sampled across temperature;
- missing covariance is not evidence that the three reactions are independent;
- the full actual PDF or coherent actual-posterior curves have not been
  reconstructed;
- scientific BBN labels and production priors remain prohibited;
- author-supplied posterior products or a clean-room reconstruction from
  original nuclear data would be required for the original functional
  posterior.

## Completion and next gate

This ingest is complete when all three publisher tables pass the pinned hash,
shape, unit, percentile-order, high-temperature-lineage and independent arXiv
cross-check validations. Completion records the public evidence and its
absence boundaries; it does not approve a scientific prior.

The successor `UQ0-RATE-PDF-AUDIT` is recorded in
`configs/physics/etr25_R0_rate_pdf_audit_v1.yaml`. It quantifies the asymmetry
between actual pointwise percentiles and the scalar log-normal approximation
while retaining the unpublished covariance as an unresolved scientific
limitation. Production remains prohibited.
