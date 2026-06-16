# ADR-0007: Arbitrary labels, balanced as groups, printed image preserved

- Status: Accepted
- Date: 2026-06-14
- Deciders: Felipe Carvajal Brown

## Context

Real deliveries vary wildly: a single pre-mixed bus, a multi-mic drum kit, two
doubled guitars, a doubled vocal, oddly-named files. A fixed set of stem "types"
cannot model all of that, and naively summing duplicates makes a doubled part
twice as loud.

## Decision

There is **no fixed stem-type set**. Every file is assigned an arbitrary
**label**; all files sharing a label are balanced **as one group**, with the
loudness target applied to the **sum** (so doubling does not inflate level). The
group is summed to stereo for the loudness measurement (matching the render
path), which also lets a label mix mono close-mics with stereo overheads. The
stems' **printed stereo image is preserved** — no auto-pan unless a `spread` is
explicitly set.

## Consequences

- One code path handles 1 or 10 files per label, any naming, any delivery shape.
- Doubled parts hit their target without coming out twice as loud.
- A regression that crashed on mixed mono/stereo groups is structurally
  prevented (everything is measured as stereo).

## References

- `CLAUDE.md` — "Arbitrary labels + group delivery"; `mixer.py` `_process_group`.
- Related: [ADR-0004](0004-internal-anchor-and-relative-balance.md), [ADR-0016](0016-engine-delivery-agnostic.md).
