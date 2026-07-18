# ADR-0037: Stereo-width + tilt knob promoted from post-1.0 into v0.8

- Status: Accepted
- Date: 2026-07-18
- Deciders: Felipe Carvajal Brown

## Context

Two master-tone widenings are the only sanctioned DSP features left in Keel's
backlog: a **deterministic stereo-width** control (post-1.0 list) and a **single
broadband tilt knob** (ADR-0031, scheduled post-1.0). Both were parked past the
1.0 DSP freeze on purpose — each touches the master math and carries a DSP-SYNC
mirror to the plugin, and the old plan wanted the 1.0 freeze to be clean.

The release-ladder redesign (ADR-0036) makes 1.0 the feature-complete launch, so
these two features move *before* it. The freeze-safety concern that kept them
post-1.0 is handled instead by a dedicated stabilization milestone (v0.9,
ADR-0038), not by deferral.

## Decision

Schedule **both** carve-outs in **`v0.8.0-beta`**, landing in the Python engine
(CLI/GUI) and mirrored into the plugin C++ chain per the DSP SYNC RULE
(ADR-0029). Both are **opt-in and off/neutral by default**, so Keel's
byte-identical deterministic defaults and the "printed stereo image preserved"
promise are unchanged for anyone who does not turn them on.

- **Stereo-width** — a flat linear M/S side-gain (NOT EQ; a single scalar on the
  side signal). It is placed **before** the oversampled true-peak limiter so the
  -1 dBTP guarantee still holds after widening. Off by default (side-gain = 1.0).
- **Tilt knob** — one deterministic broadband brighter/darker curve on the master.
  NOT per-band, NOT mid/side (those remain explicit non-goals). Neutral by default
  (tilt = 0). This is the single permitted widening of master tone beyond the
  existing fixed tilt, exactly as ADR-0031 scoped it.

Each is a new master-math change, so each must be implemented in `mastering.py` /
`recipes.py`, mirrored into `plugin/Source/`, and A/B-checked — then locked and
proven in v0.9 (ADR-0038) before the 1.0 freeze.

## Consequences

- 1.0 ships feature-complete: the sanctioned tone widenings are in, not promised.
- Determinism and the default master are preserved (both features default off).
- The TP guarantee is preserved by construction (width sits before the limiter).
- Two fresh DSP-SYNC obligations are incurred in v0.8; they are discharged and
  verified in v0.9's parity harness rather than left as manual promises.
- ADR-0031's *scheduling* (post-1.0) is superseded; its *scope* decision (one
  broadband tilt only, no M/S EQ, no multiband) is carried forward unchanged.

## Alternatives considered

- **One feature now, one post-1.0.** Smaller DSP surface before the freeze, but
  leaves 1.0 not-quite-feature-complete and splits a coherent "master widenings"
  milestone. Rejected given the v0.9 settle milestone already de-risks the freeze.
- **Keep both post-1.0 (ADR-0031 as-was).** Cleanest freeze, least complete 1.0.
  Rejected by ADR-0036.

## References

- `ROADMAP.md` "Road to 1.0" (`v0.8.0-beta`) + Post-1.0.
- Supersedes the post-1.0 **scheduling** of
  [ADR-0031](0031-master-tilt-knob-carveout.md) (its scope stands).
- Related: [ADR-0036](0036-release-ladder-v07-to-v10.md) (the ladder),
  [ADR-0038](0038-dsp-parity-harness-freeze-gate.md) (settle/verify),
  [ADR-0029](0029-plugin-self-contained-master.md) (DSP SYNC RULE),
  [ADR-0001](0001-scope-balance-and-master-only.md) (scope boundary these amend),
  [ADR-0006](0006-oversampled-true-peak.md) (the TP limiter width sits before).
