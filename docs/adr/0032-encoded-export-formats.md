# ADR-0032: Encoded export formats; DAW project files stay out

- Status: Accepted
- Date: 2026-06-22
- Deciders: Felipe Carvajal Brown

## Context

Keel outputs plain 24-bit PCM WAV (ADR-0010). "No DAW project writing" was a
non-goal, but it conflated two different things: writing DAW *session* files
(.als/.logicx — a huge per-DAW maintenance surface) and emitting *other audio
encodings* (MP3/OGG/FLAC/AAC), which users reasonably want for delivery. v0.7
already adds multi-target loudness export and post-codec true-peak re-measurement,
so encoded output is a natural fit.

## Decision

Add **encoded audio export** — MP3, OGG, FLAC, AAC (and others) alongside WAV —
to the v0.7 delivery milestone. **DAW project / session file** writing remains a
non-goal.

Determinism boundary: the byte-identical guarantee stays a **PCM/WAV** promise.
FLAC is lossless/bit-exact; the lossy formats are deterministic only *given the
same encoder and version* and are explicitly outside the byte-identical guarantee.
This pairs with v0.7's post-codec true-peak check (lossy encoding inflates peaks).

## Consequences

- Richer delivery without leaving the deterministic engine's core promise behind.
- A new dependency on an encoder (e.g. ffmpeg) is implied — a v0.7 build decision.
- The "no DAW project writing" non-goal is clarified, not removed.
- Refines ADR-0010 (24-bit PCM) for the export surface.

## References

- `ROADMAP.md` v0.7 + non-goals.
- Related: [ADR-0010](0010-24-bit-no-dither.md).
