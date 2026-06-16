# ADR-0010: 24-bit output, dither deferred

- Status: Accepted
- Date: 2026-06-14
- Deciders: Felipe Carvajal Brown

## Context

Bit-depth reduction (e.g. to 16-bit) introduces quantization error that should be
masked with dither. Dither is only meaningful when actually reducing depth.

## Decision

Render mixes and masters at **24-bit PCM** in and out. Because there is no
bit-depth reduction in the current path, **no dither is applied**. Dither is
explicitly deferred until/unless Keel ever exports below 24-bit.

## Consequences

- No dither code to maintain or to make deterministic today.
- Output is high-resolution and transcode-friendly.
- A future 16-bit export option must add (deterministic) dither at that point —
  tracked in the roadmap.

## References

- `mixer.py` / `mastering.py` `sf.write(..., subtype="PCM_24")`.
- `ROADMAP.md` Phase 2 — "Dither on export if/when rendering below 24-bit".
