# WHY-NOT benchmark interruption and resume contract

Status: implementation contract for new W1 PRyMordial runs

`scripts/why_not_benchmark.py` checkpoints W1 after every completed warm
repetition. A new run writes `resume_state.json` atomically in its persistent
output directory. If the process or SSH session ends, rerun the exact command
with `--resume` and the same `--output-dir`.

Resume is accepted only when all frozen identity fields match exactly:

- baseline, source revision, adapter and protocol hashes;
- parameter-schema and exact parameter values;
- environment-lock and hardware-inventory hashes;
- batch sizes, repetition count, and hourly price.

The runner also reimports PRyMordial and recomputes the reference abundance.
Each reference abundance must agree with the checkpoint at relative tolerance
`1e-12` before completed repetitions are skipped. New timing rows contain a
`run_attempt_id`; setup work for resumed attempts is recorded separately as
`resume_import` and `resume_reference_solve`.

The checkpoint preserves all duration samples, failure count, measured solver
time, and maximum abundance drift. Final summaries therefore use the complete
set of pre- and post-interruption warm repetitions. Cumulative accounted wall
and CPU time is updated at every repetition checkpoint and becomes the final
resource report. The logical run ID and original start time remain unchanged
across attempts.

## Boundaries

- Resume currently applies only to W1 because it is the multi-hour sequential
  baseline. W0, W2, and W3 fail closed if `--resume` is requested.
- Runs created before this contract do not contain `resume_state.json` and are
  intentionally not resumable. Their partial timing rows may be audited, but
  they cannot be promoted into a completed summary by skipping work.
- Work inside an interrupted, incomplete repetition is rerun. Resource usage
  after the last atomic checkpoint and before a hard process kill cannot be
  reconstructed, so the resource report may undercount at most that uncommitted
  interval. Clean scheduler termination should still be preferred.
- A completed state cannot be resumed or appended. A new scientific attempt
  requires a new output directory and run ID.

This is an operational reliability feature. It does not change solver physics,
accept a posterior result, or authorize Track B production.
