# ADR-SOLVER-FACTORIAL-v1: matched-physics solver factorization

Status: execution protocol prepared; scientific and compute sign-off pending

Date: 2026-07-22

Task: `SOL-01` / `P2-solver-matrix` / `P2-discrepancy-factorization`

## Decision

Solver comparison is a controlled factorial experiment over five registered
factors, not a comparison of tool names:

| Factor | Meaning | Examples |
|---|---|---|
| `E` | numerical engine, integrator, tolerances, precision and linear algebra | PArthENoPE, AlterBBN, LINX, PRIMAT |
| `R` | central nuclear rates, uncertainty model and compilation | PArthENoPE-like, PRIMAT-2023, NACRE-II-like |
| `W` | weak rates, neutrino thermal history and neutron-lifetime treatment | solver-native or matched registered implementation |
| `X` | standard or non-standard expansion implementation | standard null, registered stiff/reheating extension |
| `nu` | nuclide/reaction network topology and screening rules | key or full network |

An observed difference may be called an `engine discrepancy` only when
`R,W,X,nu` are held fixed and the numerical convergence floor has been
measured. Otherwise it is labeled `pipeline discrepancy` with the unmatched
factors listed.

## Registered solver roles

| ID | Tool/network | Role | Current availability |
|---|---|---|---|
| `S0` | project-modified PArthENoPE | primary extension high-fidelity candidate | blocked: source not supplied |
| `S1` | project-modified AlterBBN | legacy/extension engineering cross-check | blocked: source not supplied |
| `S2` | official PArthENoPE v3 | standard/rate-handling regression | acquisition pending |
| `S3` | PRyMordial NACRE-II-like | conservative explicit-rate baseline | exact source executable |
| `S4` | PRyMordial PRIMAT-like | rate-compilation baseline | configuration pending |
| `S5` | LINX `key_PArthENoPE` | differentiable core-network baseline | exact source executable; adapter pending |
| `S6` | LINX `key_PRIMAT_2023` | differentiable PRIMAT-rate baseline | exact source executable |
| `S7` | LINX `full_PRIMAT_2023` | full-network cost/stability stress test | adapter pending |
| `S8` | direct PRIMAT v0.3.2 | independent precision audit | exact source and C backend executable |

Availability is an operational statement, not scientific acceptance.

## Experiment blocks

### F0 — convention and numerical floor

Before factor attribution, every available path must use the same abundance
convention and report at least `Y_p` and `D/H`. At the standard fiducial point:

1. scan float64 tolerances until an abundance convergence plateau is visible;
2. record cold and warm execution, failures, compiler and backend;
3. compare small/key network conventions without interpreting the difference
   as an engine effect;
4. reject silent NaN, clipping, implicit fallback or a success exit code with
   failed internal diagnostics.

### F1 — matched standard-BBN blocks

Each block changes one factor while all feasible remaining factors are fixed:

1. **Engine match**: vary `E`, hold `R,W,X,nu` fixed;
2. **Rate-library match**: vary `R`, hold `E,W,X,nu` fixed;
3. **Weak-physics match**: vary `W`, hold `E,R,X,nu` fixed;
4. **Network match**: vary `nu`, hold `E,R,W,X` fixed.

At least 20 standard points are required. The point manifest must include the
fiducial, observationally relevant baryon-density/lifetime region, rate
perturbations, numerical boundaries and deterministic seeds where applicable.

### F2 — matched extension blocks

After the authoritative `X` contract is available, repeat at least 20
non-standard points. An extension comparison is invalid if two adapters use
different physical definitions, units, transition variables or normalization.
`kappa10 -> dd0` and `DeltaNeff -> dd0_rad` are currently prohibited mappings
because their conversion is absent from the supplied public source.

## Required outputs

Every cell emits:

- `run_manifest.json`: factor tuple, code revisions, build flags, environment,
  parameter/config hashes and physical node;
- `points.jsonl`: canonical inputs and adapter-transformed inputs;
- `abundances.jsonl`: values, units, conventions and structured status;
- `numerical_scan.json`: tolerance/precision convergence;
- `jacobians.json`: method, step sizes, finite fraction and repeatability;
- `factor_comparison.json`: absolute, observationally normalized and Jacobian
  differences;
- `resource_report.json`: CPU-core-hours, GPU-hours, memory, wall time and cost;
- `failures.jsonl`: every explicit failure and fallback decision.

## Acceptance and interpretation

A path enters production only after standard regression, tolerance convergence,
source/build recording, separate cold/warm measurement, structured failures and
independent unit/definition review. Every comparison reports:

- absolute abundance difference;
- difference normalized by total registered observational uncertainty;
- local Jacobian difference;
- posterior median/interval impact when the likelihood exists;
- flagship decision-boundary impact;
- whether the difference is explained by numerical tolerance.

Residual matched differences above the numerical floor enter an explicit
hierarchical discrepancy layer. They cannot be removed by selecting the most
favorable solver.

## Frozen boundaries

- S8 remains required at the fiducial, at least 100 posterior-region points,
  at least 100 flagship-boundary points, each key functional mode at
  `-2,-1,0,+1,+2 sigma`, and 20 adversarial points.
- S1 is an engineering cross-check and cannot alone define an independent
  nuclear-data extreme.
- A minimum of two independent implementations is required for ordinary
  cross-solver language; `solver-independent` remains prohibited without at
  least three matched implementations.
- Missing factors are reported as unsupported and never silently emulated by a
  competitor adapter.

## Gate status and sign-off

This document prepares the protocol but does not freeze Track B. Execution is
blocked on S0/S1 assets, the rate registry and the authoritative extension
contract.

- A00 scientific lead: pending;
- A04 solver validation: pending;
- A07 compute validation: pending.
