# ADR-0031: Master-tone carve-out — a single broadband tilt knob

- Status: Accepted
- Date: 2026-06-22
- Deciders: Felipe Carvajal Brown

## Context

ADR-0001 keeps Keel to balance + master only, with no tone shaping in the mix
stage; the master stage carries only a *fixed*, gentle tilt (HPF 28 / low-shelf
+1\@110 / air +1.5\@9k). Reviewing competitor features (Ozone-style M/S EQ and
multiband compression), the question arose whether to widen master-bus tone.

Full M/S EQ / multiband is tone-shaping by definition — exactly the "suite" Keel
defines itself against — and adds real complexity plus a heavy DSP-SYNC burden.
But a single broadband tilt (brighter/darker) is a different, much smaller thing.

## Decision

Allow **one deterministic broadband master tilt knob** (opt-in), and only that.
NOT per-band, NOT mid/side. It is the single permitted widening of master tone
beyond the existing fixed tilt. Because it touches the master math, it carries a
DSP-SYNC mirror to the plugin (ADR-0029) and is scheduled **post-1.0**, past the
1.0 DSP freeze. M/S EQ and multiband compression remain explicit non-goals.

## Consequences

- A modest corrective tone control without becoming a tone-shaping suite.
- Determinism preserved (one fixed-shape broadband curve per setting).
- Implementation is post-1.0 and must be mirrored Python <-> C++ and re-A/B'd.
- Amends ADR-0001's "no tone shaping" boundary narrowly and deliberately.

## References

- `ROADMAP.md` Post-1.0 + non-goals.
- Related: [ADR-0001](0001-scope-balance-and-master-only.md),
  [ADR-0003](0003-master-loudness-target.md),
  [ADR-0029](0029-plugin-self-contained-master.md).
