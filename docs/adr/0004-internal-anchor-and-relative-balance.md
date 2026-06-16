# ADR-0004: Per-stem internal anchor -20 LUFS + relative LU balance

- Status: Accepted
- Date: 2026-06-14
- Deciders: Felipe Carvajal Brown

## Context

A balanced mix means each instrument sits at its intended *perceived* loudness.
Working from raw stem peaks or RMS is unreliable across different sources. A
perceptual, repeatable basis is needed for the balance numbers to mean the same
thing on any delivery.

## Decision

Normalize each stem-group to an internal **-20 LUFS** anchor, then apply a
**relative balance in LU measured against the vocal** (vocals = 0; more negative
= quieter). The recipe carries those relative offsets
(`DEFAULT_BALANCE`), not absolute gains. This follows loudness-balancing practice
(Ward/Reiss, model of loudness and partial loudness).

## Consequences

- Balance values are portable and meaningful: "-3 LU vs vocal" is the same
  intent on any song.
- The mix leaves headroom (bus peaks near -6 dBFS) for the master stage.
- Vocal-anchored numbers assume a vocal-forward idiom; instrumental material just
  treats the 0-reference label as the anchor.

## References

- `CLAUDE.md` — internal anchor / relative balance.
- `recipes.py` `DEFAULT_BALANCE`; `mixer.py` `INTERNAL_ANCHOR_LUFS`.
- Related: [ADR-0007](0007-group-delivery.md).
