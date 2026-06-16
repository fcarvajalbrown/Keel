# ADR-0005: Master chain — oversampled soft-clip then true-peak limiter

- Status: Accepted
- Date: 2026-06-14
- Deciders: Felipe Carvajal Brown

## Context

Reaching a competitive loudness cleanly is hard: a limiter alone, pushed hard,
pumps and dulls transients; a hard clipper alone aliases into audible fizz. The
"loud but clean" masters (e.g. modern metal) use a specific topology.

## Decision

Master chain order: tone (HPF 28 / low-shelf / air / gentle glue comp) ->
pre-normalize toward target -> **oversampled tanh soft-clip** (rounds the
sharpest transients) -> **4x-oversampled true-peak limiter** -> normalize to the
**exact** target LUFS -> true-peak safety. The clipper takes the very top so the
limiter has less to do and stays clean; clipping a hair above the limiter ceiling
spreads the loudness work between the two stages.

## Consequences

- At -14 the chain barely limits, leaving ~3-4 dB true-peak headroom; it still
  holds up cleanly when pushed to -10/-11.
- The final exact-LUFS step is a turn-down vs. the limited signal, so peaks only
  drop — no re-clipping.
- This is a deliberate DSP *approach*; changing it requires research + citations
  ("research-before-tweak").

## References

- `CLAUDE.md` — master chain; `mastering.py` `_internal_master`.
- Related: [ADR-0003](0003-master-loudness-target.md), [ADR-0006](0006-oversampled-true-peak.md).
