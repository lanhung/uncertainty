# Sensitivity-atlas R0 slice reproduction v1

Status: **executed; frozen acceptance failed**

This calibration reproduces the `d(p,gamma)3He`, `d(d,n)3He` and
`d(d,p)t` abundance-response slice published by the 2026 BBN sensitivity
atlas. It runs `q=-1,0,+1` with the frozen public PRyMordial source and
compares centered abundance derivatives with the published
`tau_n`-normalised PRIMAT table.

The atlas result repository is pinned at
`d3ea1838d9450673698f07b7c6b8971efb87d0fd`; the independent solver run is
pinned at PRyMordial
`725d8a8db3ad5ea2630580d825c9d0d69ed76533`.

Important limitation: the atlas publishes PDFs but does not publish the
generating scripts or its PRyMordial commit. This is therefore an independent
public-code comparison, not a bitwise rerun. Passing it is C0 calibration
evidence only. It does not accept the project R0 prior, authorize production,
or establish novelty.

The registered run completed all 10 abundance solves with zero structured
failures and zero central-repeat drift. The three D/H derivatives agreed in
sign and within the frozen numerical tolerances. The complete baseline did not
pass, however:

- the public PRyMordial run's central `Li7/H x 1e10` is about `0.05594`
  below each atlas-table central value (roughly one percent);
- the extremely small `d(p,gamma)3He -> Yp` derivative has the opposite sign
  from the published table, although its absolute scale is only a few parts
  in `10^-6`.

The immutable evidence digest is
`412adfd0614a4d7239338ea56349428cd4b4eef8338e047f8669841656cf618b`.
This execution is retained as a reproducibility-gap result and grants no
`UQ0-NATIVE-UQ-REPRO` progress. The frozen thresholds were not relaxed after
observing the run.
