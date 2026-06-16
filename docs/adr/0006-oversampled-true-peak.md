# ADR-0006: 4x polyphase-FIR oversampling for true-peak metering/limiting

- Status: Accepted
- Date: 2026-06-14
- Deciders: Felipe Carvajal Brown

## Context

Sample-peak meters miss **intersample peaks** (ISPs) — reconstruction overshoots
between samples that can be up to ~+3 dB and cause clipping after D/A or lossy
transcode. BS.1770-4 specifies true-peak measurement via oversampling.

## Decision

Implement a real **4x polyphase-FIR oversampling** true-peak meter and run the
limiter/soft-clip on the oversampled signal (scipy `resample_poly`, Kaiser beta
12). At 4x, intersample peaks become real samples the limiter can actually catch.
If scipy is unavailable, degrade gracefully to a sample-peak meter/limiter at base
rate rather than crash.

## Consequences

- True-peak numbers in the QC report are trustworthy; the -1 dBTP ceiling is real.
- scipy is a core dependency (also used by pyloudnorm); accepted.
- The graceful-fallback path is lower-fidelity but keeps the engine runnable.

## References

- `meters.py` (true-peak meter); `mastering.py` `_up`/`_down`/`_os_limit`.
- BS.1770-4; ISP/oversampling research (cited in code).
- Related: [ADR-0005](0005-master-chain-clip-then-limit.md).
