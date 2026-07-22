# Offline heartbeat end-to-end regression v1

Status: **ACCEPTED — EXECUTION ONLY**

Run: `497f490f-5c04-4cd6-8a97-df410bfd8de8`

Task: `EXEC-HEARTBEAT-OFFLINE-E2E-v1`

## Result

The frozen regression completed on `autodl-westb-01` at main `705d2e7` while
the worker's normal Tailscale control path was unavailable. The runner removed
all inherited proxy variables, confirmed `http://127.0.0.1:1` was unreachable,
and then ran the eight-step demo under the host-level `ops-e2e` lease.

- atomic midrun checkpoint: `1/8`;
- final checkpoint and terminal heartbeat: `8/8`;
- terminal metric: `demo_fraction=1`;
- ordered unique buffered events: 11;
- outbox SHA256: `8971c7a8254bc368e25b28c124ea18cd857fd36f86d2951a3912c8b4af15fbc5`;
- lease release detected in `0.0000848 s`;
- independent lease reacquisition in `0.0882 s`;
- wall time: `48.7001 s`;
- estimated westb cost at CNY 2.88/hour: CNY `0.03896`;
- structured failures: 0.

The immutable outbox was copied to the Vultr control host, dry-run validated,
and replayed in order through the reviewed replay tool. All 11 events received
durable acknowledgements, none was a duplicate, and the replay working copy was
fully drained. The final offline bundle validator accepted all eight checks.

## Gate invariance

Immediately before replay, the dashboard reported scientific gate `21%` and
execution milestones `33%` at revision 275. Immediately after replay it
reported scientific gate `21%` and execution milestones `50%` at revision 286.
The scientific gate therefore remained unchanged while the execution-only task
advanced from pending to done.

## Evidence

The complete bundle is under
`artifacts/ops/OFFLINE-HEARTBEAT-E2E-v1/run-20260722T200435Z/`. It contains the
protocol-bound manifest, checkpoints, run and lease metadata, original outbox,
replay archive/report, resource report, checksum manifest and accepted
validation report.

This result validates control-plane durability only. It grants zero scientific
gate credit and makes no solver, posterior, Fisher, rate or physics claim.
