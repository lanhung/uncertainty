# Physics endpoints v1

Status: definitions prepared; detector/ranking thresholds and sign-off pending

Date: 2026-07-22

Registry: `configs/physics/physics_endpoints_v1.yaml`

## Primary physical outputs

The analysis reports the following as co-primary physical endpoints rather than
selecting whichever looks largest after unblinding:

1. `V_detectable_full / V_detectable_baseline`, stratified by real detector
   data or named forecast;
2. each core parameter's signed median shift normalized by the registered
   reference standard deviation;
3. each core credible-interval width ratio;
4. registered posterior-mode or exclusion-boundary topology change;
5. model probability or Bayes factor only after prior robustness passes;
6. standard-to-nonstandard reaction sensitivity reordering;
7. nuclear rate value-of-information under a registered precision
   intervention.

The null-effect boundary for posterior location is absolute shift below `0.1
sigma`; the null interval-width band is `[0.95, 1.05]`; topology must remain
unchanged. These boundaries are inherited by H1/H3 and the Fisher G0 rule.

No numeric detector-volume, rank-correlation or nuclear-intervention success
threshold is invented here. Those require the missing detector/extension and
NUC-v1 contracts and must be frozen before Track B unblinding.

## Primary computational outputs

Computational claims use high-fidelity calls at target posterior
risk/coverage, end-to-end wall time, CPU-core-hours, GPU-hours, monetary cost,
ESS/hour, 1,000-SBC total cost, nuisance-dimension scaling and explicit
failure/OOD/fallback fraction.

A direct stack that passes fidelity and fits on at most two workers within 14
days and 672 worker-hours blocks a speed-only emulator claim. A hybrid speed
claim requires at least `10x` fewer high-fidelity calls or `5x` measured
end-to-end wall-time reduction at matched fidelity.

MSE, NLL, CRPS, energy score, single-forward speed, parameter count and GPU
utilization are auxiliary. None can replace the physical or end-to-end
computational endpoints.

## Strata and claim boundaries

- The main observation and N0 neutron-lifetime analysis are reported separately
  from every mandatory data/N1-N3 robustness stratum.
- Real SGWB results and detector forecasts are stored and plotted separately.
- Lithium is a null test and cannot support a “lithium problem solved” claim.
- Fixed-degeneracy slices are conditional responses, not constraints.
- `solver-independent` remains prohibited without at least three matched
  implementations.

## Negative results and stopping

Crossing no effect threshold is a valid result. It closes or narrows the
corresponding route; it does not authorize broader priors, alternative primary
data or an expanded endpoint search. In particular, Fisher G0 leaves
Pilot-10k unauthorized and closes the proposed Nature Astronomy effect route
for that tested mechanism.

## Sign-off

- A00 scientific lead: pending;
- A03 statistics validation: pending;
- A09 publication/claim audit: pending.

Track B remains NOT FROZEN until these sign-offs and the outstanding numeric
threshold contracts are complete.
