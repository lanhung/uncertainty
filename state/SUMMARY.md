# uncertainty — live research status

_Generated: 2026-07-21T23:54:24+00:00; revision: 59_

**Overall plan completion: 6%.** This is effort-weighted execution progress, not scientific confidence.

Status counts — running: 3, blocked: 3, pending: 24, done: 3

## Live now
- **P0-LIT-01** — Competitor matrix: LINX, PRyMordial, PRIMAT, PArthENoPE, AlterBBN, ABCMB+LINX [running]
  - progress: 0% (0/8 baselines); ETA: —
  - owner: vultr; attempt: 1; run_id: —
  - heartbeat age: 638 s
- **P0-NEUTRON-01** — Preregister neutron-lifetime N0-N3 baseline and robustness models [running]
  - progress: 0% (0/1 decisions); ETA: —
  - owner: vultr; attempt: 1; run_id: —
  - heartbeat age: 638 s
- **P0-OBS-01** — Preregister primary and stress-test D/H, Y_p, CMB and GW datasets [running]
  - progress: 0% (0/1 decisions); ETA: —
  - owner: vultr; attempt: 1; run_id: —
  - heartbeat age: 638 s

## Blocked / needs a decision
- **P0-repo-migrate** — Migrate existing scientific code into lanhung/uncertainty and remove local paths [blocked]
  - depends on: P0-code-inventory
  - note: inventory found no legacy BBNet/MCMC/solver source; requires an original source path/archive or a separately registered upstream acquisition decision
- **P0-tailnet** — Join control + two workers to the private tailnet [blocked]
  - progress: 67% (2/3 hosts); ETA: —
  - owner: uncertainty-autodl-westb-01-elastic; attempt: 1; run_id: —
  - note: control and westb joined (2/3); second eligible worker awaits persistent storage and an idle window
- **P0-worker-bootstrap** — Bootstrap two shared AutoDL nodes as elastic workers [blocked]
  - progress: 50% (1/2 workers); ETA: —
  - owner: uncertainty-autodl-westb-01-elastic; attempt: 1; run_id: —
  - blocked by: P0-tailnet
  - note: westb ready (1/2); remaining workers lack /root/autodl-fs and are occupied, so policy forbids bootstrap

## Pending
- **P0-WHY-NOT-01** — Write why-not-LINX/PRyMordial/PRIMAT and emulator economics memo [pending]
  - progress: 0% (0/1 memos); ETA: —
  - blocked by: P0-LIT-01
- **P0-benchmark** — Benchmark cold/warm, FP64, batch, CPU, RAM, I/O and failure rates [pending]
  - progress: 0% (0/6 configurations); ETA: —
  - blocked by: P0-solvers-build
- **P0-env-lock** — Create environment lock, pyproject, CI, pre-commit and make smoke [pending]
  - progress: 0% (0/5 checks); ETA: —
  - blocked by: P0-repo-migrate
- **P0-reproduce-bbnet** — Reproduce one known BBNet result end-to-end through the monitored pipeline [pending]
  - progress: 0% (0/3 checks); ETA: —
  - blocked by: P0-solvers-build
- **P0-solvers-build** — Build project PArthENoPE/AlterBBN plus LINX and PRyMordial reference paths [pending]
  - progress: 0% (0/4 solvers); ETA: —
  - blocked by: P0-env-lock
- **P1-hardsoft-posterior** — EXP-A01 hard/soft comparison in the full 10-D physical posterior [pending]
  - progress: 0% (0/16 chains); ETA: —
  - blocked by: P1-mcmc-refactor
- **P1-kappa-identifiability** — EXP-A02 kappa identifiability for consistency relation, free n_t and free T_re [pending]
  - progress: 0% (0/7 runs); ETA: —
  - blocked by: P1-mcmc-refactor
- **P1-mcmc-refactor** — Refactor MCMC to >=4 chains with split-R-hat, ESS, MCSE and resume [pending]
  - progress: 0% (0/6 checks); ETA: —
  - blocked by: P0-reproduce-bbnet
- **P1-schramm-slices** — Produce preregistered Schramm-style conditional and marginalized slices [pending]
  - progress: 0% (0/6 figures); ETA: —
  - blocked by: P1-kappa-identifiability
- **P1-trackA-freeze** — Freeze Track A claims, tables, figures and reproducibility package [pending]
  - progress: 0% (0/3 signoffs); ETA: —
  - blocked by: P1-hardsoft-posterior, P1-schramm-slices
- **P2-discrepancy-factorization** — Separate engine, rate-library, weak-rate and extension discrepancies [pending]
  - progress: 0% (0/4 factors); ETA: —
  - blocked by: P2-unified-adapter
- **P2-functional-rate-basis** — Construct 2-3 functional uncertainty modes for the three leading deuterium reactions [pending]
  - progress: 0% (0/3 reactions); ETA: —
  - blocked by: P2-rate-registry
- **P2-rate-registry** — Reaction-rate registry with central curves, sigma(T), covariance and provenance [pending]
  - progress: 0% (0/12 reactions); ETA: —
  - blocked by: P2-solver-matrix
- **P2-solver-matrix** — Implement initial solver/rate matrix S0, S1, S5 and S6 [pending]
  - progress: 0% (0/4 paths); ETA: —
  - blocked by: P0-solvers-build
- **P2-unified-adapter** — Unified simulate(theta, q, a, neutron, solver, network, precision) adapter [pending]
  - progress: 0% (0/4 paths); ETA: —
  - blocked by: P2-solver-matrix, P2-rate-registry
- **P2.5-fisher-propagation** — Propagate rate, shape, solver and observation covariance into approximate posteriors [pending]
  - progress: 0% (0/4 scenarios); ETA: —
  - blocked by: P2.5-jacobians, P2-discrepancy-factorization
- **P2.5-gate-report** — Issue G0/G1/G2/G3 Fisher Gate decision and authorize or stop Pilot-10k [pending]
  - progress: 0% (0/3 signoffs); ETA: —
  - blocked by: P2.5-fisher-propagation, P0-WHY-NOT-01
- **P2.5-jacobians** — Compute J_theta, J_q and function-shape proxies at representative points [pending]
  - progress: 0% (0/64 points); ETA: —
  - blocked by: P2-unified-adapter, P0-OBS-01, P0-NEUTRON-01
- **P3-cross-solver** — Cross-solver and cross-rate-library validation including PRIMAT-family rates [pending]
  - progress: 0% (0/4 baselines); ETA: —
  - blocked by: P3-pilot-10k
- **P3-nonstandard-reordering** — Test rate-rank inversion under stiff and other non-standard expansion histories [pending]
  - progress: 0% (0/4 scenarios); ETA: —
  - blocked by: P3-standard-atlas-regression
- **P3-nuclear-voi** — Quantify nuclear-experiment value-of-information for early-Universe/GW parameters [pending]
  - progress: 0% (0/6 interventions); ETA: —
  - blocked by: P3-nonstandard-reordering, P3-cross-solver
- **P3-pilot-10k** — Pilot-10k targeted/active-learning dataset; forbidden under G0 [pending]
  - progress: 0% (0/10000 samples); ETA: —
  - blocked by: P3-pilot-1k
- **P3-pilot-1k** — Pilot-1k real-solver labels with checksums, failures and throughput ledger [pending]
  - progress: 0% (0/1000 samples); ETA: —
  - blocked by: P2.5-gate-report
- **P3-standard-atlas-regression** — Reproduce known standard-BBN reaction sensitivity ranking as a regression test [pending]
  - progress: 0% (0/12 reactions); ETA: —
  - blocked by: P3-pilot-10k

## Done
- **P0-code-inventory** — Inventory all existing BBNet, MCMC, solver patches, data and model files [done]
  - progress: 100% (1/1 inventories); ETA: —
  - owner: vultr; attempt: 1; run_id: —
  - note: inspected Git/GitHub, Vultr and registered workers; no legacy scientific migration input was found
  - artifacts: [docs/inventory/EXISTING_SCIENTIFIC_ASSETS_v1.md](https://github.com/lanhung/uncertainty/blob/main/docs/inventory/EXISTING_SCIENTIFIC_ASSETS_v1.md), [manifests/inventory/existing_scientific_assets_v1.json](https://github.com/lanhung/uncertainty/blob/main/manifests/inventory/existing_scientific_assets_v1.json)
- **P0-control-plane** — Deploy project-isolated research-ops service on the shared Vultr host [done]
  - progress: 100% (5/5 checks); ETA: —
  - owner: vultr; attempt: 1; run_id: —
  - note: project-isolated control service, auth, ledger, local ops-status branch and health check ready; systemd persistence pending sandbox boundary
- **P0-ops-e2e** — Validate ledger, heartbeat, stale detection and ops-status snapshots [done]
  - progress: 100% (4/4 checks); ETA: —
  - owner: uncertainty-autodl-westb-01-elastic; attempt: 1; run_id: 57fa65e3-24ba-4559-884f-a652c6c5df0c
  - blocked by: P0-worker-bootstrap
  - metrics: demo_fraction=1.0
  - note: METRIC demo_fraction=1.000000
