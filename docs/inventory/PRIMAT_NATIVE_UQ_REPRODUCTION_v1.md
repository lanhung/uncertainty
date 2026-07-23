# PRIMAT native-UQ reproduction v1

Status: **executed; accepted as one C0 native-UQ calibration baseline**

The registered worker run completed 1,000/1,000 draws with the compiled C
backend, zero structured failures, and exact agreement between the first 16
parallel draws and an independent serial replay. The central abundance
reference, covariance, correlation, finite-output, positivity, and nonzero
standard-deviation checks all passed. The immutable evidence digest is
`a351c12594dd24dd277864a886db22b02d3da8e1259023de1489ff6ec5376374`.

This protocol reproduces the native Monte Carlo uncertainty propagation in
PRIMAT v0.3.2 at commit
`21ff8f39fa18e3937e9fdf386cfa982361bfdfce`. It is a C0 public calibration
baseline. It does **not** select or validate the project R0 prior, reproduce an
ETR25 actual rate PDF, count as UQ1 direct-Monte-Carlo truth, authorize
production, or establish a novelty claim.

## Frozen native model

The exact compiled C backend runs the public `small` network at
`Omega_b h^2 = 0.02237`, `Delta Neff = 0`, and central neutron lifetime
`878.3 s`. PRIMAT's upstream-native prior varies all 12 thermonuclear rate
latents independently as standard normals and draws the neutron lifetime from
`Normal(878.3 s, 0.5^2 s^2)`. Nuclear and plasma QED corrections are enabled,
and the native Monte Carlo rate-rescale cap is 30.

These choices intentionally reproduce PRIMAT's own native uncertainty model.
They are not a substitute for the coherent ETR25/public-data prior required by
the project.

## Registered execution and resumability

The command is:

```bash
python scripts/run_primat_native_uq_reproduction.py \
  --source-root /absolute/path/to/frozen/primat \
  --output-dir /persistent/path/PRIMAT-NATIVE-UQ-REPRODUCTION-v1 \
  --hourly-price-cny <worker-price>
```

The runner refuses source revision or byte drift, a dirty checkout, an
installation not attributable to that checkout, environment-lock drift, and
the absence of `primat._primat_c`. It always passes `force_backend="c"`; the
known-stale Python Monte Carlo path is prohibited.

The 1,000 samples use base seed `2026072301`, 20 C worker threads, and durable
prefix checkpoints at 100, 300, and 1,000 draws. Each complete MC sample
matrix is written to a versioned file before one atomic state pointer advances;
an interruption can therefore expose either the complete old checkpoint or the
complete new checkpoint, never a mixed pair. Restarting the same command
reconstructs a C-origin `MCResult` only after checking protocol, source,
parameters, seed, hashes, shapes, and finiteness, then asks PRIMAT to extend the
seed-indexed stream.

After the main run, a fresh 16-draw, one-thread C run must equal the first 16
parallel samples bit for bit. This checks that batching and thread count do not
change the registered seed prefix.

## Outputs and acceptance

The output directory contains:

- `artifact.json`, with a canonical evidence digest and explicit C0 boundary;
- `samples.npy` and `samples.tsv` for `YPBBN`, `DoH`, `He3oH`, and `Li7oH`;
- `covariance.tsv` and `correlation.tsv`, both using `ddof=1`;
- `checkpoint.json` and versioned `checkpoint_samples_<N>.npy` files;
- append-only `timings.jsonl` and `failures.jsonl`;
- `resource_report.json`.

Acceptance requires 1,000 finite, positive abundance rows, positive sample
standard deviation for all four outputs, finite symmetric covariance and
correlation matrices, a unit correlation diagonal, an empty structured-failure
ledger, agreement with the frozen central PRIMAT forward baseline, and exact
parallel/serial prefix replay. Statistics at `N=100`, `300`, and `1,000` are
diagnostics only.

Validate independently with:

```bash
python scripts/validate_primat_native_uq_reproduction.py \
  /persistent/path/PRIMAT-NATIVE-UQ-REPRODUCTION-v1/artifact.json
```

The validator re-hashes every registered file and recomputes summaries,
quantiles, covariance, correlation, replay equality, checkpoint consistency,
timing/resume accounting, and cost arithmetic from the raw evidence.

## Upstream limitations preserved

PRIMAT's native `run_mc` output does not return the sampled rate latents or
neutron-lifetime draws. A compiled-C batch failure aborts without identifying a
per-draw failure. The reverse-rate cap is constructed from median/QED rates
rather than rebuilt per draw. The upstream independence assumption is not an
experimental covariance model. Passing this protocol therefore establishes
only a public native-C calibration baseline.
