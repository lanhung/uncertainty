# Worker environment validation v1

Status: passed on `autodl-westb-01`

Captured: 2026-07-22

Task: `P0-env-lock`

## Result

The project-scoped CPython 3.11.15 environments were built from the checked-in
locks on the available westb worker. Every run held the appropriate host-level
resource lease and released it successfully.

| Path | Result |
|---|---|
| general solver CPU | JAX 0.7.2 used the CPU backend with x64 enabled; its FP64 linear solve exactly matched SciPy |
| training GPU | PyTorch 2.12.1+cu130 used the physical RTX 4090, CUDA was available, and the FP64 solve completed on device |
| W0 LINX | exact source revision, JAX 0.4.28, hash-verified Interpax 0.3.1 sidecar, and 12-reaction source import passed |
| W1 PRyMordial | exact source revision, 63-reaction table load, and frozen Python dependency smoke passed |
| W2 PRIMAT | exact source revision built its C backend; a standard small-network run returned finite physical `Y_p` and D/H |
| W3 ABCMB | exact source revision, JAX 0.8.1 x64, and its bundled 12-reaction LINX network import passed |

The six raw manifests are stored under `artifacts/environments/`. Their lock
hashes and source revisions are checked in unit tests.

## Transfer provenance

The AutoDL academic proxy was too slow for first-time multi-gigabyte wheel
downloads. The identical checked-in locks were resolved with the registered
uv 0.11.28 on the control host, caches were compressed, transferred over the
existing authenticated SSH channel, verified by SHA256 on the worker, and then
consumed by the standard worker bootstrap scripts. No package version or lock
was changed during transfer.

## Scientific boundary

These results establish executable environments only. They are not registered
cold/warm timing measurements, matched-physics solver comparisons, posterior
recovery, or accuracy validation. In particular, the PRIMAT smoke abundance is
not a new scientific result and must not enter a claim or figure.
