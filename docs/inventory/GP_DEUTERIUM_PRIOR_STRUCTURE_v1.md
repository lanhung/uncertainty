# 2026 GP deuterium-prior structure audit v1

Status: **structure captured; exact abundance rerun blocked by upstream release**

The arXiv v1 source for `2604.16600` is byte-pinned and its public method
contract is recorded in
`configs/benchmarks/gp_deuterium_prior_structure_v1.yaml`.

The paper models `d(d,n)3He` and `d(d,p)t` S factors with Gaussian-process
posteriors, while `d(p,gamma)3He` is Gaussian in log S. Its fiducial kernel is
an additive squared-exponential plus Matérn-1/4 kernel in log-energy distance.
Within-experiment normalization covariance is retained, hyperparameters are
fixed after leave-dataset-out optimization, and every posterior S-factor curve
is thermally averaged into one coherent rate curve. Independent
temperature-bin noise is not an equivalent representation.

The published abundance references are captured, including the
Planck-marginalized result `1e5 D/H = 2.442 +/- 0.040`.

The paper explicitly defers its analysis-code release. The fitted
hyperparameters, exact experimental data bundle, posterior draws and random
seeds are also absent. Consequently this audit is not an independent rerun of
the abundance distribution and is not eligible for a
`UQ0-NATIVE-UQ-REPRO` progress increment under ADR-0008. It remains C0
structure/provenance evidence and will fail closed until the upstream release
provides enough material for a seeded rerun.
