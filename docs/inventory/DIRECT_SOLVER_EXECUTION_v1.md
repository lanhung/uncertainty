# Direct solver execution v1

Status: forward paths executed; LINX gradient path rejected

Captured: 2026-07-22

Task: `P0-solvers-build` / `P0-WHY-NOT-01`

## Result

The frozen LINX and PRyMordial sources were executed on
`autodl-westb-01` in their accepted project-scoped environments. These were
upstream source-level executions, not the registered 30-repetition common
benchmark, posterior comparison or SBC campaign.

| Baseline | Source execution | Forward result | Timing evidence | Acceptance boundary |
|---|---|---|---|---|
| LINX `W0` | upstream `scripts/test_SBBN_PRIMAT.py` | standard BBN completed; all five displayed quantities agreed with the script's PRIMAT references within 0.3% | 55.806 s cold forward; 0.725 s compiled forward | forward smoke accepted; gradient/HMC path rejected because one of 15 gradient components was `NaN` |
| PRyMordial `W1` | upstream `runPRyM_julia.py` | small and large Python networks returned finite physical abundances | 7.809 s small; 9.016 s large | Python source smoke accepted; optional Julia backend was absent and was not silently substituted |

LINX's value-and-gradient path compiled in 289.587 s and reported a 3.281 s
subsequent call, but the first gradient component was non-finite. The upstream
script printed `Differentiability test failed.` while returning process exit
code zero. Repository evidence therefore records `failed_nan` explicitly and
forbids using this run as an accepted gradient or HMC baseline. A zero shell
exit status alone is not an acceptance criterion.

The raw logs and machine-readable extraction are:

- `artifacts/solver-build/linx-test-SBBN-PRIMAT-v1.log`;
- `artifacts/solver-build/prymordial-standard-v1.log`;
- `artifacts/solver-build/DIRECT_SOLVER_SMOKE_v1.json`.

## Scientific boundary

These single upstream executions establish that both direct forward paths can
run from the frozen sources. They do not establish common-scenario throughput,
repeatability, gradients, posterior fidelity, cost, or emulator necessity.
`P0-WHY-NOT-01` remains open. `P0-solvers-build` remains partial because the
project-modified PArthENoPE and AlterBBN sources have not been supplied.
