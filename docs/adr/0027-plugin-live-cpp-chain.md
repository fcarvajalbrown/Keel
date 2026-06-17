# ADR-0027: Plugin runs a live C++ master chain (preview) + Python finalize

- Status: Superseded by [ADR-0029](0029-plugin-self-contained-master.md)
- Date: 2026-06-17
- Deciders: Felipe Carvajal Brown
- Supersedes: [ADR-0026](0026-plugin-architecture-juce-shell.md) (the
  offline-only "shell out on Apply, defer the C++ port" model)
- Amends (plugin context only): [ADR-0003](0003-master-loudness-target.md)
  (exact -14 LUFS), [ADR-0013](0013-keel-py-library-facade.md) (don't fork the DSP)

> **Superseded by [ADR-0029](0029-plugin-self-contained-master.md).** The live
> C++ master chain stays, but the offline **Finalize** (shell out to the bundled
> frozen engine for a byte-identical exact-loudness file) is dropped: the live
> chain already masters, and a DAW export bakes it in. The plugin is now a
> self-contained real-time master with a static Makeup gain; exact -14/-1
> delivery lives only in the CLI/GUI. The DSP SYNC RULE below still applies.

## Context

ADR-0026 decided the plugin would be a thin shell with **no DSP in C++**: it would
pass audio through, show live meters, and produce the master only via an offline
**Apply** that shells out to the frozen Python engine. After the build-green spike
shipped (`plugin/`, the passthrough + meters + Apply-stub), the user tried it in a
DAW and rejected the feel: a master you only hear *after* an offline Apply is
clunky. The request: it should work **live, like iZotope Ozone** — insert it on
the master bus, hear the mastered sound in real time, tweak, with the meters
moving.

Research (research-before-tweak, ~5 sources):

- **Ozone genuinely processes live.** Its EQ / dynamics / imager / Maximizer all
  run in real time; you hear the master as it plays and tweak instantly. The AI
  "Master Assistant" only does a short analysis pass to *configure* the modules,
  then it is an ordinary real-time plugin.
- **A live loudness "target" is approximate, not exact.** Ozone's Maximizer
  "Target LUFS" merely sets the limiter **Threshold** expected to land near that
  loudness; the achieved integrated LUFS depends on the material and is verified
  with a meter.
- **This is physics, not a tool limitation.** Integrated LUFS is an average over
  the *whole* program, so a single-pass real-time plugin cannot know it until the
  song ends. Exact integrated LUFS needs a two-pass / offline operation (scan the
  whole file, then apply gain).
- **Pros prefer it that way:** control dynamics live (clip / limit / saturate),
  then *verify* loudness against references — rather than force an exact loudness
  on render, which can hurt quality.

Mapped onto Keel's master chain (tone -> pre-normalize -> oversampled soft-clip
-> 4x oversampled true-peak limiter -> normalize to exact LUFS -> TP safety): the
first four stages are **real-time-capable**; only the **exact-LUFS normalize** is
whole-program / offline. So a live Keel plugin is possible — but you **cannot
shell out to Python in real time** (not RT-safe; ADR-0026 rejected embedded
Python for the same reason). Live therefore *requires* a C++ port of the
real-time chain, which is exactly what ADR-0026 deferred. A further hard truth:
Keel's limiter is **pedalboard's** (ADR-0005); a C++ reimplementation will sound
*close* but will **not** be byte-identical to `build.py` / `gui.py`.

## Decision

The plugin runs a **live C++ master chain as a faithful preview**, and delivers
the **byte-identical master from the Python engine on Finalize**.

1. **Live (C++, real-time):** port Keel's real-time master stages to C++ — tone
   (HPF 28 / low-shelf / air / glue comp), oversampled tanh soft-clip, 4x
   oversampled true-peak limiter — so the user **hears the Keel master live** and
   tweaks it, with the existing live LUFS / true-peak meters. The true-peak
   ceiling (-1 dBTP) is honored live (the limiter is real-time). This is a
   **preview**: it represents the master character, not the exact delivered bytes.

2. **Loudness (live = approximate, exact on Finalize):** live, the chain targets
   ~-14 LUFS via the limiter threshold / makeup gain (Ozone-style), and the live
   meter shows where it actually lands. **Exact -14 LUFS / -1 dBTP is applied only
   on Finalize.** This amends ADR-0003 *for the plugin only* — the standalone CLI
   and GUI still guarantee exact -14 at all times.

3. **Finalize (offline, Python = authoritative):** on Finalize / render, the
   plugin bounces the program audio to a temp WAV and **shells out to the bundled
   frozen Python engine** to master it — **byte-identical** to `build.py` /
   `gui.py` (exact -14 LUFS, -1 dBTP, deterministic). The delivered file is always
   the validated Keel master, preserving Keel's "same stems + same recipe ->
   identical output, every front-end" identity. (This keeps ADR-0026's shell-out
   mechanism, now for Finalize rather than for everything.)

4. **Two implementations, kept in sync by hand.** The C++ live chain and
   `mastering.py` are now **two disconnected implementations of the same master
   character.** The Python engine is the **reference**; the C++ chain is a port of
   it. This amends ADR-0013: the CLI and GUI still share the one Python core and
   must not fork it; the plugin's live preview is the **single, deliberate
   exception**, justified by real-time playback, and is explicitly a *preview*,
   not a second delivery engine (delivery stays Python via Finalize).

   **DSP SYNC RULE:** any change to the master math in the Python engine
   (`mastering.py`, `recipes.py` `DEFAULT_MASTER` / `PRESETS`, the -20 LUFS
   anchor, the -14 / -1 dBTP targets) **must be mirrored into the C++ live chain**
   (`plugin/Source/`) and re-checked against the Python reference (A-B / null the
   same file), or the preview drifts from the Finalized file. Recorded in
   `CLAUDE.md` (Architecture + Locked DSP sections) so it is seen every session.

## Consequences

- **Best-feel UX:** the plugin behaves like a normal mastering plugin — insert,
  hear it, tweak — which is what the user asked for. The offline step shrinks to a
  single Finalize/render that locks exact loudness.
- **New work: a C++ DSP port** of the real-time stages (the spike's passthrough
  becomes the live chain). It must be validated as a *faithful preview* against
  the Python reference (A-B; "close enough" by ear, since pedalboard's limiter
  will not null exactly). The exact-loudness normalize is **not** ported — Finalize
  owns it.
- **Dual maintenance:** every master-math change is now a two-place edit (Python
  + C++). The DSP SYNC RULE and the reference/preview framing exist to contain the
  drift risk; the determinism guarantee for *delivered* files is unaffected (still
  Python).
- **Still bundles the frozen engine** for Finalize (~97 MB), as ADR-0026 — no
  system Python needed. CI must build the frozen engine, then the plugin.
- **Preview vs delivered can differ slightly** (the C++ limiter vs pedalboard, and
  approximate vs exact loudness). This is acceptable and matches the industry
  (what you monitor through is a representation; the render is authoritative). The
  UI should make "preview now, exact on Finalize" clear.
- **ARA2** remains the later polish (whole-clip Finalize with no manual bounce).
- Licensing unchanged from ADR-0026 (JUCE AGPLv3 / Starter; review VST3 + ARA SDK
  terms before public distribution).

## References

- Supersedes [ADR-0026](0026-plugin-architecture-juce-shell.md); amends
  [ADR-0003](0003-master-loudness-target.md), [ADR-0013](0013-keel-py-library-facade.md).
- Master chain / limiter: [ADR-0005](0005-master-chain-clip-then-limit.md),
  [ADR-0006](0006-oversampled-true-peak.md).
- Ozone is real-time: <https://musictech.com/reviews/plug-ins/izotope-ozone-12-review/>,
  <https://www.izotope.com/products/ozone-advanced>
- Maximizer "Target LUFS" sets the threshold:
  <https://docs.izotope.com/ozone11/en/maximizer/index.html>
- Integrated LUFS is whole-program / needs two-pass:
  <https://aes2.org/resources/audio-topics/loudness-project/loudness-normalization/>
- Control dynamics live, verify loudness after:
  <https://www.masteringthemix.com/blogs/learn/mastering-the-art-of-limiting-and-loudness>
