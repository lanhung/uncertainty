# Science critical path v3.1 — superseded

> Status: **SUPERSEDED**  
> Superseded on: 2026-07-23  
> Replacement: [`SCIENCE_CRITICAL_PATH_v4.md`](SCIENCE_CRITICAL_PATH_v4.md)  
> Governing decision: [`ADR-0008-self-contained-fast-track.md`](../decisions/ADR-0008-self-contained-fast-track.md)

This version placed exact reproduction of the 2026 sensitivity-atlas slice and the unpublished GP deuterium abundance analysis on the dependency chain for the project-owned R0 prior.

The repository audit established that those exact reproductions require upstream generator code, configurations, fitted hyperparameters, data products, posterior draws or seeds that are not publicly available. Their frozen failed/blocked evidence remains valid and is not converted into a pass.

The active path now separates:

```text
mandatory PRIMAT / PRyMordial / LINX core baselines
from
non-blocking atlas / GP external paper audits
```

Use:

- `plan/plan.yaml` version 6;
- `docs/ops/SCIENCE_CRITICAL_PATH_v4.md`;
- `docs/ops/FAST_TRACK_MILESTONES_v1.md`;
- `configs/physics/nuclear_prior_R0_reference_v1.yaml`.

The full v3.1 text remains available in Git history at commit `ac5a495abf2da5ebce9412e74df6d84b6268f86f`.
