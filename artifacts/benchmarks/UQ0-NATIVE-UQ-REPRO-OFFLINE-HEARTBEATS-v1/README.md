# UQ0 native-UQ offline-heartbeat archive v1

These four outbox files were emitted on `autodl-westb-01` while its Tailscale
client was logged out. They are retained byte-for-byte for audit, but must not
be replayed:

- `99835f83-1978-48ff-a3ed-0e62e68778e1` is a refused online-start attempt;
- `586bee78-1e3d-4097-ba9c-d7aceebdb7fd` is the first PRyMordial run whose
  numerical results passed but whose artifact lacked the required empty
  failure ledger;
- `18f6ecc2-e3ba-409f-8006-8c4a49339e50` is the corrected, accepted
  PRyMordial run;
- `38770fbe-13c5-4b40-97df-3bb47d846516` is the completed LINX run that
  failed its frozen tolerance-plateau threshold.

The pre-fix wrapper would replay the LINX child exit as a terminal failure of
the five-component parent task. It would also replay superseded progress from
the first PRyMordial attempt. The control ledger is therefore updated from the
independently validated artifacts with `taskctl artifact`, `note`, and an
absolute `2/5` progress event. The worker copies are moved into a
`superseded-do-not-replay` directory rather than deleted.

SHA256:

```text
eff737b556ffdd52b17c7018583cd40371adef3aa6fa1a39c3b46fa5c293b342  UQ0-NATIVE-UQ-REPRO-18f6ecc2-e3ba-409f-8006-8c4a49339e50.ndjson
59b015b37c78a1a61cc74da08cc929e2ccff6618486ee102e181b71ec2a3a8d9  UQ0-NATIVE-UQ-REPRO-38770fbe-13c5-4b40-97df-3bb47d846516.ndjson
7b463a47fcf171dbbb32bf8b363fad3e91c7049e9f833e9157e1a0adb5b101ac  UQ0-NATIVE-UQ-REPRO-586bee78-1e3d-4097-ba9c-d7aceebdb7fd.ndjson
d26f2a5ab75d7f3adbd43fb8dc5c3ce93ba0d1217a91224424d13a7d0ccabe80  UQ0-NATIVE-UQ-REPRO-99835f83-1978-48ff-a3ed-0e62e68778e1.ndjson
```
