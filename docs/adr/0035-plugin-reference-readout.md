# ADR-0035: Plugin Reference control is a passive loudness/peak readout

- Status: Accepted
- Date: 2026-06-23
- Deciders: Felipe Carvajal Brown

## Context

The plugin exposed a "Reference" toggle (`reference` bool parameter) wired through
APVTS to a button, but `processBlock` never read it — a dead control, the mirror
of the dead-toggle situation ADR-0030 fixed for Bus-glue. The open question for
`v0.5.0-beta` (recorded in `ROADMAP.md` and the hand-off) was whether to **wire**
it into the live chain or **remove** it.

Wiring a real reference *match* into the live C++ chain would mean a live
spectral / loudness match — i.e. Matchering-style processing in real time. That is
out of scope for the plugin for two reasons: (1) Matchering is an offline, Python
analysis (ADR-0009) and porting it live is a large, non-deterministic body of
work; (2) a genuine ML/spectral match collides with Keel's deterministic,
balance+master-only doctrine. Meanwhile the plugin's by-ear Makeup workflow has a
real gap: users want to know *how loud and how peaky a track they admire is* so
they can aim Makeup at it. That need is answered by a measurement, not a match.

## Decision

Replace the dead toggle with a **passive reference readout**: the user loads a
reference audio file, the plugin measures it **once, offline, on a background
thread**, and shows its **integrated LUFS (BS.1770-4, fully gated)** and
**true-peak (4x oversampled)** next to the live master meters. There is **no live
match** — the spectral/ML reference path stays the offline Matchering feature in
the CLI/GUI (ADR-0009).

Mechanically:
- The `reference` **parameter is removed** (it was never an audio-affecting,
  host-automatable on/off). The reference is a *file*, persisted as a
  `referencePath` property in the APVTS state tree and re-measured on project load.
- New display-only atomics (`referenceLufs`, `referenceTruePeak`,
  `referenceLoading`) carry the worker's result to the UI; a "Load reference…" /
  "Clear" pair and a readout label replace the toggle.
- The integrated-LUFS gating (absolute −70 LUFS, then relative −10 LU over 400 ms
  blocks at 100 ms hop) matches what `meters.py` / pyloudnorm report for the same
  file, so the readout is comparable to a CLI/GUI measurement of that track.

## Consequences

- The Reference control now does something honest and useful, and the
  Makeup-by-ear target gap is narrowed (you can read the reference's loudness and
  aim for it).
- **No DSP SYNC obligation (ADR-0029):** this is metering/UI only — it does not
  touch the master tone math in either `mastering.py` or the C++ live chain. The
  two master implementations are unchanged.
- The plugin still does **not** alter audio based on the reference; a true match
  remains the offline Matchering path in the CLI/GUI.
- Measuring a whole song is bounded (12-minute read cap) and runs off the message
  thread so the editor never blocks.

## References

- `plugin/Source/PluginProcessor.cpp` (`measureReferenceStats`, `loadReference`,
  `clearReference`, `setStateInformation`), `plugin/Source/PluginEditor.cpp`
  (load/clear buttons + readout).
- Related: [ADR-0009](0009-optional-matchering-reference.md) (offline Matchering
  match stays the real match), [ADR-0029](0029-plugin-self-contained-master.md)
  (DSP SYNC RULE — not triggered here),
  [ADR-0030](0030-plugin-bus-glue-toggle.md) (the sibling dead-toggle fix).
