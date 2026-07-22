# WHY-NOT PRyMordial standard-fiducial runtime v1

Status: registered runtime slice complete; rate, posterior and extension comparisons pending

Captured: 2026-07-22

Task: `P0-WHY-NOT-01`

## Result

The exact W1 PRyMordial source at
`725d8a8db3ad5ea2630580d825c9d0d69ed76533` was run through its Python backend
on `autodl-westb-01`. The frozen adapter selected the small 12-reaction network,
PRIMAT-like rate tables, recomputation of the thermodynamic background and bulk
weak rates, and reuse of stored thermal weak corrections. The input point came
from `configs/physics/parameter_schema.yaml`: `Omega_b h2 = 0.02237`, `Delta
N_eff = 0`, and `tau_n = 878.3 s`, with extension coordinates at the standard-
model null.

The registered timing slice completed with no failures:

| Measurement | Result |
|---|---:|
| cold package import | 0.484 s |
| cold first solve | 6.412 s |
| 30 warm scalar solves, median | 5.90683 s/point |
| warm scalar p95 | 5.99220 s/point |
| 30 sequential 64-point workloads, median | 375.05736 s/batch |
| sequential 64-point median | 5.86027 s/point |
| timed warm points | 1,950 |
| structured failures | 0 |
| maximum repeated-output drift | 0 |
| peak resident memory | 215,351,296 bytes |
| measured wall time | 11,447.088 s |
| estimated worker cost at the registered node price | CNY 9.158 |

At this point PRyMordial returned `Y_P(BBN) = 0.2468834991`, `D/H =
2.4441162056e-5`, and `N_eff = 3.0443885203`. These values are preserved as
solver outputs for traceability, not as an observational or scientific claim.

The 64-point workload is explicitly labeled as sequential calls because this
upstream path has no native vectorized batch API. Every timing record is
preserved in `timings.jsonl`, and the empty `failures.jsonl` is tracked. The
generic validator independently recomputed hashes, counts, summaries and cost
arithmetic and passed 21 integrity checks.

## Scientific boundary

This completes only W1's standard-fiducial runtime slice. It does not exercise
the full scalar-rate marginalization, any functional rate mode, the registered
non-standard expansion point, matched posterior recovery or the end-to-end
workload projection. The old likelihood assets and the shared extension
contract are unavailable, so `posterior_metrics.json` records `not_run` rather
than a fabricated result.

The result therefore cannot decide whether direct PRyMordial is sufficient for
production inference. `P0-WHY-NOT-01` and the overall emulator-necessity
conclusion remain open and undetermined.
