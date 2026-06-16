# ADR-0008: Filename label auto-detect via anchored token matching + scan review

- Status: Accepted
- Date: 2026-06-15
- Deciders: Felipe Carvajal Brown

## Context

Auto-labelling from filenames is convenient but error-prone. A naive
substring match mislabels ("ride" inside "pride", "oh" inside "john"), and drum
kits ship as per-component mics (kick/snare/toms/overheads) whose names rarely
contain "drum" — so they scatter into `other` instead of grouping as one kit.

## Decision

Tokenize filenames (split on separators, camelCase, letter/digit runs; drop pure
digits) and match aliases **anchored at a token start** — so short aliases like
`oh` hit an "OH" overhead but never "john". Kit-piece names are listed under
`drums` so a multi-mic kit collapses into one group. Auto-detect is only a first
guess written into `keel.json`; a **`--scan` mapping review** prints per-label
counts and a `[check]` callout for anything in `other`, so a mislabel is visible
before render.

## Consequences

- Real multitracks (raw rock kit, synth-heavy multitrack) auto-label correctly.
- `STEM_ALIASES` is an editable hint table, not a constraint.
- The user always has a chance to fix labels before committing a render.

## References

- `mixer.py` `_tokenize`/`_match_label`; `build.py` `_print_mapping_review`.
- Related: [ADR-0007](0007-group-delivery.md), [ADR-0012](0012-keel-json-source-of-truth.md).
