# ABCMB bundled-LINX scalar/native-batch consistency v1

Status: complete; numerical consistency not accepted

Captured: 2026-07-22

Task: `P0-WHY-NOT-01`

Run: `run-20260722T113106Z`

## Frozen experiment

The scan was frozen in `configs/benchmarks/abcmb_linx_batch_consistency_v1.yaml`
before execution and bound to ABCMB commit
`5eabbab4ed7e53f264e16024743d1ba517845c37`, bundled LINX tree
`59b3ab7b3ada7d7ff6484920e0e29291cf4a084e`, the standard-BBN fiducial point,
the accepted observation normalization and the W3 background numerics.

Eight cases varied abundance tolerance and weak-rate sampling. Each case ran
one scalar and one native 64-point compile/solve plus three warm scalar and
three warm native-batch repetitions. All 64 expected timing records are
preserved.

## Result

All eight cases completed with zero failures, zero repeat drift and zero
within-batch spread. The three frozen candidates stayed inside the `0.01`
observation-sigma scalar/batch budget:

| Candidate | Maximum scalar/batch difference |
|---|---:|
| registered | 0.00268640 sigma |
| tolerance tight | 0.00529014 sigma |
| tolerance tighter | 0.00033423 sigma |

Both convergence requirements failed:

| Plateau | Measured maximum | Frozen limit | Result |
|---|---:|---:|---|
| tolerance | 0.00476910 sigma | 0.001 sigma | failed |
| weak-rate sampling | 0.02745561 sigma | 0.001 sigma | failed |

The run used `0.0817940` worker-hours, `0.2194960` measured CPU core-hours,
zero GPU-hours and an estimated CNY `0.23557`. Peak resident memory was
1,761,742,848 bytes.

## Decision boundary

The run is complete but the numerical gate is not accepted. It provides no
gradient, Fisher, HMC/NUTS, posterior, extension or full ABCMB pipeline label.
An extended convergence scan must be preregistered without relaxing the failed
plateau threshold. The full WHY-NOT conclusion remains undetermined.
