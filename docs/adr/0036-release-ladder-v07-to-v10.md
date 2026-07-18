# ADR-0036: Release ladder v0.7 -> v1.0 (plugin depth -> DSP carve-outs -> DSP settle -> launch)

- Status: Accepted
- Date: 2026-07-18
- Deciders: Felipe Carvajal Brown

## Context

Through `v0.6.0-beta` the roadmap staged the road to 1.0 as: `v0.7.0-beta`
(go-to-market) then `v1.0.0` (sign + freeze + stamp), with the two sanctioned
master-tone widenings (deterministic stereo-width and a single broadband tilt
knob) parked in **post-1.0** specifically to stay clear of the 1.0 DSP freeze.

Reviewing that shape, two things were unsatisfying. First, the plugin is the
weakest link in the product: its by-ear Makeup gain is steered by a *momentary*
LUFS meter while streaming services normalize on *integrated* LUFS, so users aim
at the wrong number — a credibility gap, not a missing feature. A researched
backlog of plugin metering/UX depth already exists (ADR-0033 oversampling
selector; the v0.5 candidate list) but had no milestone home. Second, shipping
1.0 while the only remaining "real features" sit unbuilt in post-1.0 makes 1.0
feel less than feature-complete.

Pulling the DSP carve-outs pre-1.0 addresses the second point but reintroduces the
first risk the old plan avoided: fresh master-math landing right before a freeze,
with no settling time. The resolution is to give the DSP its own dedicated
stabilization milestone so it is provably stable *before* the freeze.

## Decision

Restructure the road to 1.0 into four milestones:

- **`v0.7.0-beta` — Plugin depth.** The full researched plugin backlog:
  metering/credibility (integrated + short-term LUFS, LRA, loudness-history graph,
  gain-reduction history, true-peak peak-hold, loudness-matched A/B bypass) +
  UX/quality-of-life (hiDPI resize, undo/redo, user presets, tooltips/first-run
  note, host-automation plumbing, accessibility labels) + the already-decided
  plugin-only oversampling-quality selector (ADR-0033). The useful additions
  (loudness-matched A/B, richer post-render meters such as LRA) are mirrored into
  the standalone GUI. **All meter/UI/packaging — no master-tone math changes, so no
  DSP SYNC in this milestone.**
- **`v0.8.0-beta` — DSP carve-outs.** Deterministic stereo-width + broadband tilt
  knob, in the Python engine (CLI/GUI) **and** mirrored into the plugin C++ chain
  per the DSP SYNC RULE. Both opt-in / off-by-default. See ADR-0037.
- **`v0.9.0-beta` — DSP settle & freeze-prep.** No new master math. Validate and
  lock the carve-outs and prove Python<->C++ parity so the 1.0 freeze stamps an
  already-stable engine. See ADR-0038.
- **`v1.0.0` — Launch.** The original `v0.7` go-to-market work (landing page,
  donation + commercial checkout, trademark verification, `README.es` full parity,
  before/after demo audio) folded together with sign + freeze + stamp. 1.0 is the
  public debut, so marketing, signing, and the DSP freeze land as one release.

The load-bearing rule: **all DSP work is complete by v0.8 and spends the whole of
v0.9 proving stable**, so v1.0's freeze is a stamp, not a fresh change.

## Consequences

- 1.0 becomes genuinely feature-complete (the two sanctioned tone widenings ship
  before it), instead of promising them post-1.0.
- The plugin's credibility gap (Makeup aimed at the wrong LUFS number) is closed in
  the first of these milestones, before any public launch.
- Go-to-market moves from `v0.7` to `v1.0`; the intermediate betas (0.7, 0.8, 0.9)
  are all engineering and are individually publishable/testable.
- The DSP freeze stays clean: a dedicated settle milestone (v0.9) guards it, rather
  than freezing math that landed one milestone earlier.
- The GUI and plugin stay versioned in lockstep at every step (CLAUDE.md
  "Versioning (STRICT)").

## Alternatives considered

- **Spread the two DSP features across v0.8 and v0.9** (stereo-width in 0.8, tilt +
  settle in 0.9). Gentlest on the freeze, but slower to feature-complete and it
  turns v0.9 into a mixed feature+settle milestone rather than a clean stabilization
  pass. Rejected in favor of finishing all DSP in v0.8 and keeping v0.9 pure settle.
- **Go-to-market at v0.9, freeze at v1.0** (keep marketing before the stamp).
  Workable, but it leaves the DSP settling *implicitly* during unrelated
  go-to-market work rather than under a dedicated, verifiable milestone, and it does
  not give 1.0 the "launch" identity. Rejected.
- **Leave the carve-outs in post-1.0 (original plan).** Keeps the freeze pristine
  but ships a 1.0 that is not feature-complete and never closes the plugin
  credibility gap before launch. Rejected.

## References

- `ROADMAP.md` "Road to 1.0".
- Related: [ADR-0037](0037-stereo-width-and-tilt-into-v08.md) (the DSP features
  promoted into v0.8), [ADR-0038](0038-dsp-parity-harness-freeze-gate.md) (the v0.9
  settle harness), [ADR-0033](0033-plugin-oversampling-selector.md) (oversampling
  selector, part of v0.7), [ADR-0029](0029-plugin-self-contained-master.md) (DSP
  SYNC RULE), [ADR-0031](0031-master-tilt-knob-carveout.md) (tilt carve-out,
  rescheduled by ADR-0037).
