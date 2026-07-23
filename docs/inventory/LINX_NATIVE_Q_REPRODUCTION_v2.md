# LINX native `nuclear_rates_q` abundance reproduction v2

Status: **accepted C0 calibration; project prior still not selected**

Task: `UQ0-NATIVE-UQ-REPRO` (`3/5` after independent validation)

V1 completed without structured failures but missed the frozen tolerance
plateau by `0.000246448` observation sigma. Before executing v2, commit
`ca5949634899bc88fb009ed4b03598ba43b11387` froze stricter numerical settings:

- candidate `rtol=3e-9`, `atol=3e-12`, `sampling_nTOp=4800`,
  `max_steps=32768`;
- tolerance comparator `rtol=1e-8`, `atol=1e-11` at the same sampling;
- sampling comparator `sampling_nTOp=2400` at the strict tolerance;
- the acceptance threshold remained exactly `0.001` observation sigma.

The westb CPU/FP64 run at exact LINX revision
`ec2e9d2ca455e8204137e884da29f5dd13a638fa` completed 42 scalar rows and 28
heterogeneous batch rows. The independent validator recomputed:

| Check | Result |
|---|---:|
| tolerance plateau | `0.0006193677` observation sigma |
| weak-rate sampling plateau | `0.0002280820` observation sigma |
| maximum scalar/batch difference | `0.0000846348` observation sigma |
| scalar repeat drift | `0` |
| batch repeat drift | `0` |
| structured failures | `0` |
| all three R0 D/H responses | nonzero and straddle central |

The run used `0.09897` worker-hours, `0.27311` CPU-core-hours, no GPU, and an
estimated CNY `0.2850`. Evidence is under
`artifacts/benchmarks/LINX-NATIVE-Q-REPRODUCTION-v2/run-20260723T102602Z/`;
its evidence digest is
`9328c7876d717a840c9b6f09572529bc7b4dc25626fe13ed278336e669beb00b`.

This accepts one public LINX native scalar-envelope calibration at claim level
C0. It does not select `NUC-v1`, reconstruct ETR25 actual rate PDFs, authorize
the production nuisance adapter, validate gradients/HMC, establish matched
cross-solver discrepancy, or supply a novelty claim.
