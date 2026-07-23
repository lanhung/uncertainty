# LINX v2 offline heartbeat disposition

Status: **archived and superseded; do not replay**

The two outboxes are retained as operational evidence only:

- `05443...ndjson` is the failed preflight that discovered the exact LINX
  environment requires an explicit YAML parser;
- `59314...ndjson` is the successful scientific run.

The successful child emitted internal `PROGRESS n/44` lines while its parent
task has total `5`. Because the wrapper invocation did not override the
default progress regex, intermediate events contain parent-invalid current
values greater than five. Replaying them would corrupt the ledger even though
the final event correctly reports accepted baseline count `3/5`.

Both files were moved on the worker to:

`outbox/superseded-do-not-replay/UQ0-NATIVE-UQ-REPRO-LINX-v2-20260723/`

and no active UQ0 outbox remains. The validated artifact is reconciled directly
through `taskctl`; these events must never be replayed.

SHA256:

```text
41b7e3009d37476f9d67d5910851f7dad09b2c03abfa45dc2f36f05d82e374e4  UQ0-NATIVE-UQ-REPRO-05443bd0-ae5f-4cbd-a044-b3f848130f6a.ndjson
be67de1969f98be642b334114e9bd64465857b0f4eb00149bab569e28233de4c  UQ0-NATIVE-UQ-REPRO-59314d6c-38cd-4634-9d78-255b3aadc341.ndjson
```
