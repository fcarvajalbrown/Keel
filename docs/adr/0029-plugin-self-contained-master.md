# ADR-0029: Plugin is a self-contained real-time master — drop Finalize

- Status: Accepted (supersedes ADR-0027)
- Date: 2026-06-17
- Deciders: Felipe Carvajal Brown
- Amends (plugin context only): [ADR-0003](0003-master-loudness-target.md)
  (exact -14 LUFS), [ADR-0013](0013-keel-py-library-facade.md) (byte-identical
  across front-ends)

## Context

ADR-0027 paired a **live C++ master preview** with an offline **Finalize** that
shelled out to the bundled frozen Python engine to produce the byte-identical,
exact -14 LUFS / -1 dBTP delivery. The live chain shipped and works; Finalize was
still a stub.

Using the live VST on the master bus in a DAW surfaced the real question: the live
chain **already masters the audio**, and a normal DAW export with the plugin active
**bakes that master into the bounce**. So a separate offline Finalize is redundant
for ordinary delivery — it duplicates, as a clunky second pass, what the export
already does. Finalize also carried real cost: bundling the ~97 MB frozen engine in
the plugin, orchestrating bounce -> temp WAV -> subprocess -> read-back, and ARA2
later just to make that seamless.

Two facts make the offline pass unnecessary for the plugin's audience:

- **Streaming re-normalizes loudness.** Spotify / YouTube / Apple normalize every
  track to their own target, so landing at -13.6 vs exactly -14.0 LUFS is inaudible
  to the listener. Exact integrated LUFS is a delivery-spec nicety, not a
  perceptual requirement.
- **The part that matters is already enforced live.** The -1 dBTP true-peak ceiling
  (which prevents clipping on lossy transcode) is held in real time by the live 4x
  oversampled limiter, so DAW exports are already TP-safe.

ADR-0027's live loudness used an **adaptive auto-makeup** that chased a slow
loudness estimate toward the target. On a fresh bounce that gain ramps up from
unity over the first seconds, so a song that starts loud would get a quieter intro
on export — an artifact unacceptable for a delivery path.

## Decision

The plugin is a **self-contained real-time master**. There is **no Finalize, no
bundled engine, no shell-out**. You deliver by **exporting from the DAW with the
plugin active**.

- **Loudness is approximate, set manually.** A **static user Makeup gain (dB)**
  drives the post-tone signal into the soft-clip / limiter; you set it by ear so
  the live LUFS meter sits at the target. This replaces ADR-0027's adaptive
  auto-makeup. Being **static**, playback and a DAW bounce are identical — no intro
  ramp. (This is how Ozone's Maximizer works: a fixed threshold/target, verified on
  a meter.)
- **True-peak is enforced live.** The 4x oversampled limiter holds the -1 dBTP
  ceiling in real time, so exports don't clip.
- **Target LUFS / preset is a meter reference**, not an auto-driver — it draws the
  target line you aim the Makeup at.
- **Exact delivery still exists — in the CLI and GUI.** `build.py` and `gui.py`
  still produce the byte-identical, deterministic, exact -14 LUFS / -1 dBTP master
  via the Python engine. Anyone who needs a guaranteed-spec file runs it there. The
  plugin deliberately trades that exactness for a **live, self-contained** master.
- **The DSP SYNC RULE still applies.** The C++ live chain and `mastering.py` remain
  two disconnected implementations of the same master character; Python is the
  reference and any master-math change must be mirrored into the C++ chain and
  re-A/B'd.

## Consequences

- **Major simplification.** No frozen-engine bundling (~97 MB), no subprocess
  orchestration, no ARA2 requirement. The plugin is a normal, self-contained
  VST3 / AU / Standalone — smaller, simpler to build and ship.
- **The "byte-identical across all front-ends" promise (ADR-0013) now holds for the
  CLI + GUI only.** The plugin delivers the **faithful preview** — close, not
  byte-identical (the C++ limiter is not pedalboard's; loudness is approximate).
  This is acceptable and matches how mastering plugins are actually used: what you
  monitor and bounce through is the master.
- **The plugin does not guarantee exact -14.** Users who need the exact number run
  the file through the GUI / CLI. The UI states this (an export note, no Finalize).
- UI change: the Finalize button is removed; a **Makeup** control is added; an
  export note explains the self-contained workflow.
- Reaffirms ADR-0027's amendment of ADR-0003 for the plugin (approximate loudness,
  verified on the meter); drops ADR-0027's offline Finalize and frozen-engine
  bundling.

## References

- Supersedes: [ADR-0027](0027-plugin-live-cpp-chain.md). Amends
  [ADR-0003](0003-master-loudness-target.md),
  [ADR-0013](0013-keel-py-library-facade.md).
- Live chain / limiter: [ADR-0005](0005-master-chain-clip-then-limit.md),
  [ADR-0006](0006-oversampled-true-peak.md).
- Ozone Maximizer target = threshold, verified on a meter:
  <https://docs.izotope.com/ozone11/en/maximizer/index.html>
- Streaming loudness normalization (exact LUFS not perceptually required at
  delivery): <https://aes2.org/resources/audio-topics/loudness-project/loudness-normalization/>
