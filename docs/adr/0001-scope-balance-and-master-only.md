# ADR-0001: Scope — balance + master only, no tone shaping in the mix

- Status: Accepted
- Date: 2026-06-14
- Deciders: Felipe Carvajal Brown

## Context

Keel receives **finished, FX-printed stems** — virtual instruments and effects
(EQ, compression, reverb) are already baked in. A general "mixing" tool would be
unbounded: per-track EQ, dynamics, sends, automation. That scope is large, hard
to make deterministic, and risks double-processing material that is already
treated.

## Decision

Keel does exactly two things: **level-balance + sum** the stems into a stereo
mix, and **master** that mix for loudness + peak safety. The mixer only
level-balances, optionally pans, and sums. It does **not** apply tone processing.
The per-stem EQ/comp/reverb fields in `recipes.py` exist solely as a corrective
escape hatch and stay empty by default. A stereo master cannot re-balance
instruments — balance is fixed in the recipe and re-mixed, never "fixed" in the
master.

## Consequences

- Predictable, explainable output; nothing is silently re-EQ'd.
- Users needing tone changes do them upstream (in their DAW), then re-print stems.
- Keeps the engine small and the DSP auditable.
- Establishes the hard boundary every later feature is checked against.

## References

- `CLAUDE.md` — "Hard scope — BALANCE + MASTER only".
- Related: [ADR-0007](0007-group-delivery.md), [ADR-0011](0011-recipes-defaults-deep-merge.md).
