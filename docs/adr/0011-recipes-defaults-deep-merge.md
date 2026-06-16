# ADR-0011: recipes.py defaults + deep-merge override model

- Status: Accepted
- Date: 2026-06-14
- Deciders: Felipe Carvajal Brown

## Context

The engine needs sensible defaults *and* per-song customization, without forcing
users to edit Python and without scattering project-specific data through the
code. The old project hardwired song-specific values into the engine.

## Decision

`recipes.py` holds only **generic `DEFAULT_*` tables** (balance/pan/spread/chain/
master) plus the `STEM_ALIASES` hint table. Per-project tweaks are passed as
small **sparse override dicts** (sourced from a song's `keel.json`) and
**deep-merged** onto the defaults: nested dicts merge, scalars/lists from the
override win, and balance for an unknown label defaults to 0.0. No song list, no
folder assumptions live in the engine.

## Consequences

- One generic engine serves any song; defaults change in one place.
- `keel.json` only needs to carry what differs from defaults.
- Clean separation: data (recipes/keel.json) vs. engine (mixer/mastering).

## References

- `recipes.py` `_deep_merge` / `mix_recipe` / `master_recipe`.
- Related: [ADR-0012](0012-keel-json-source-of-truth.md), [ADR-0016](0016-engine-delivery-agnostic.md).
