# ADR-0002: Deterministic engine, no ML, no randomness in the render path

- Status: Accepted
- Date: 2026-06-14
- Deciders: Felipe Carvajal Brown

## Context

Many modern "auto-mix / auto-master" tools use ML models or stochastic search.
That makes results non-reproducible and opaque: the same input can yield
different output, and you cannot explain *why* a move was made.

## Decision

Keel is **rule-based and deterministic**. Same stems + same recipe + same
options -> **identical output, byte for byte**, every run. No machine learning,
no randomness anywhere in the render path. Every move (loudness balance, pan,
limiter behaviour) is derived from explicit, inspectable math.

## Consequences

- Results are reproducible and reviewable; QC is a diff, not a listening guess.
- Determinism is testable — a regression test asserts byte-identical renders
  (see [ADR-0018](0018-stdlib-unittest-suite.md)).
- Rules out otherwise-tempting features (neural mixing, randomized dither
  seeding) unless they can be made deterministic.
- Forces honest engineering: if a default is wrong, it is wrong for a reason we
  can name and change.

## References

- `CLAUDE.md` — "Deterministic only", non-goals.
- Related: [ADR-0018](0018-stdlib-unittest-suite.md).
