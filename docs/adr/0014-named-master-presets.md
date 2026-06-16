# ADR-0014: Named master presets (target-only, render-time override)

- Status: Accepted
- Date: 2026-06-16
- Deciders: Felipe Carvajal Brown

## Context

Users shouldn't have to remember loudness numbers. A "house sound" picker is
wanted (streaming-safe vs loud). But a preset that also touched instrument
balance would be a large, fragile surface and would blur the line between "how
loud" and "how it's balanced".

## Decision

Ship **named master presets** that set **only** the master loudness target +
true-peak ceiling — a preset picks how loud the master lands, not how the
instruments sit. They are applied as a **live render-time override** of the
mapping's master block (an explicit `--lufs/--tp` still wins). Shipped:
`streaming` (-14, default), `loud` (-10), `broadcast` (-16), all at -1.0 dBTP.
Values are grounded in current platform norms, not arbitrary:

- streaming -14 LUFS — Spotify / YouTube / Tidal / Amazon normalization target.
- loud -10 LUFS — club/aggressive; held clean by the oversampled clip + limiter.
- broadcast -16 LUFS — Apple Music / Apple Podcasts / AES TD1008 (quieter, more
  dynamic). Note: EBU R128 *TV/radio* broadcast is the much quieter -23 LUFS.

Users can save their own presets (a small JSON store) via the GUI.

## Consequences

- One flag picks a competitive, platform-correct loudness.
- Master-target-only keeps the feature small and predictable.
- The -1 dBTP ceiling is constant: streaming services recommend true peaks at/
  under -1 dBTP so lossy transcoding doesn't clip.

## References

- `recipes.py` `PRESETS` / `preset_master`; `build.py --preset`; `userpresets.py`.
- Related: [ADR-0003](0003-master-loudness-target.md), [ADR-0012](0012-keel-json-source-of-truth.md).
