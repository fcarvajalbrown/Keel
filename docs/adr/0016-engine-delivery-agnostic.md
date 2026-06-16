# ADR-0016: Engine stays delivery-agnostic (no project assumptions)

- Status: Accepted
- Date: 2026-06-14
- Deciders: Felipe Carvajal Brown

## Context

Keel was lifted on 2026-06-14 from an album project where it was hardwired to
that album's songs (fixed song list, `../song{N}/` folder assumptions, a fixed
five-type stem matcher). To be usable by any musician it had to be decoupled.

## Decision

The engine handles **any stem-delivery shape** and encodes **no project
assumptions**: no song lists, no fixed stem-type set, no folder-layout
assumptions in `mixer.py` / `mastering.py` / `meters.py`. Deliveries may be a
pre-mixed bus, a multi-mic kit, doubles, or unknown names (-> `other`).
`STEM_ALIASES` is only an editable auto-detect hint, never a constraint.

## Consequences

- One engine serves any song or album; the de-coupling refactor is complete and
  must stay that way.
- New features are checked against this rule — do not reintroduce song/folder
  hardcoding.
- Saved as a standing memory (`engine-stays-delivery-agnostic`).

## References

- `CLAUDE.md` history note; saved memory `engine-stays-delivery-agnostic`.
- Related: [ADR-0007](0007-group-delivery.md), [ADR-0011](0011-recipes-defaults-deep-merge.md).
