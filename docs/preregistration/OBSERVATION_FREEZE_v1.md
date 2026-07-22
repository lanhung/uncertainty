# OBS-v1 observation freeze

Status: **decision frozen; Track B gate closed**
Decision date: 2026-07-21 UTC
Task: `P0-OBS-01` / scientific blocker `OBS-01`

## Frozen main choices

The abundance likelihood uses LBT Project IV `Y_p = 0.2458 ± 0.0013`
and the Cooke et al. homogeneous sample `10^5(D/H)_P = 2.527 ± 0.030`.
The initial CMB stage uses the Planck 2018
`TT,TE,EE+lowE+lensing` Gaussian summary
`Omega_b h^2 = 0.02237 ± 0.00015`.

These choices were made before inspecting any Track B production effect size.
Cooke 2018 was chosen for the main D/H result because it is a homogeneous,
conservative sample. The newer Kislitsyn compilation is mandatory robustness,
not an alternative to select after seeing a favorable result.

The machine-readable definitions are:

- `configs/data/abundance_OBS-v1.yaml`;
- `configs/data/cmb_data_v1.yaml`;
- `configs/data/gw_data_v1.yaml`;
- `manifests/data/OBS-v1-sources.yaml`.

## Mandatory robustness matrix

| Observable | Dataset | Frozen role |
|---|---|---|
| `Y_p` | Aver, Olive & Skillman 2015, `0.2449 ± 0.0040` | legacy helium |
| `Y_p` | EMPRESS v2, `0.2402 +0.0040/-0.0040` | low-helium stress |
| `D/H` | Kislitsyn all available, `2.533 ± 0.024` | updated-compilation stress |
| `D/H` | Kislitsyn precision nine, `2.501 ± 0.028` | precision-subset stress |
| CMB | full Planck chain/likelihood and one registered alternative | CMB-form stress |
| GW | alternative registered likelihood/spectrum parameterization | GW-form stress |

Alternative measurements that reuse objects or calibration information are not
independent likelihood factors. They are separate analyses unless a documented
covariance or hierarchical nuisance construction is introduced.

## Lithium and forecasts

`Li/H` is excluded from the default likelihood and retained only as an
independent null test. LISA, ET and CE products are forecasts and must be stored,
reported and plotted separately from observed constraints.

## LVK implementation boundary

The observed GW target is the LVK O1–O4a stiff-equation-of-state analysis in
`LIGO-P2500150-v13` / arXiv `2510.26848v2`, including the compact-binary
background treatment. The public DCC entry currently exposes the manuscript but
not a standalone machine-readable stiff-era posterior or likelihood product.
Consequently, `GW-v1` is registered but **not production-ready**. Production use
requires either an official product or a separately reviewed reimplementation.
Plot digitization may not be presented as the official likelihood.

## Version and integrity policy

Every cited source has an immutable version URL and SHA256 in the source
manifest. Published scalar summary statistics are the frozen data product for
the abundance and initial CMB likelihoods. Any later raw table, posterior chain,
or likelihood download receives its own checksum and parser test before use.

## Change control and sign-off

Any post-freeze change goes to `docs/preregistration/DEVIATION_LOG.md` and is
labeled confirmatory or exploratory before rerunning inference. Later O4b or
newer products enter monthly audit first; they do not silently replace O1–O4a.

Prepared by: Codex acting in the A04 observations/preregistration role.
A00 scientific lead sign-off: **pending**.
Independent data/likelihood verification: **pending**.
Track B status: **NOT FROZEN**.
