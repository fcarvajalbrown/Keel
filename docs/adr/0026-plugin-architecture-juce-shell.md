# ADR-0026: Phase 5 plugin is a JUCE/C++ shell that shells out to the Python engine

- Status: Accepted
- Date: 2026-06-17
- Deciders: Felipe Carvajal Brown

## Context

Phase 5 is the DAW plugin (VST3 / AU). The hard constraint is Keel's locked DSP:
the master **normalizes to an exact integrated LUFS** (-14) and uses a look-ahead,
oversampled true-peak limiter (ADR-0003, ADR-0005, ADR-0006). Integrated LUFS is a
**whole-program** measurement — it needs the entire signal — so the master is
**inherently an offline / two-pass operation**, not a sample-by-sample real-time
process. A real-time "live master" would have to chase short-term loudness with a
gain rider, which is a different algorithm and would break the locked exact-LUFS
decision. The industry confirms this: exact-LUFS plugins (HoRNet ZeroLoud, Youlean)
hit their target via an offline "Apply" analysis pass, not in real time.

A second constraint is the project rule **do not fork the DSP** (ADR-0013): the CLI
(`build.py`) and GUI (`gui.py`) already drive one shared Python core via
`import keel`. The plugin must not become a second, drifting copy of the mastering
math.

Three ways to build a sellable VST3/AU were researched:

- **JUCE/C++** — industry standard; dual-licensed AGPLv3 + commercial; binaries are
  sellable. JUCE 8 **Starter tier is free up to USD 20k/yr revenue, explicitly
  including donations/sponsorship**; above that, Indie is USD 800 perpetual.
- **VENOM (Python-in-JUCE via pybind11)** — GPLv3, which collides with Keel's
  commercial license (ADR-0023, ADR-0025). Rejected.
- **Embedded Python interpreter** — not real-time-safe (GIL, no parallel threads),
  and ships 100 MB+ of numpy/scipy. The viable patterns still need a C++ shell and
  either delegate real-time work to C++ or run Python out-of-process.

The plugin model was decided with the user as **hybrid**: real-time pass-through
with **live meters** + an **offline "Apply"** that runs the true Keel master.

## Decision

The plugin is a **thin JUCE/C++ shell**, not a reimplementation of the engine.

- **Scope = master-bus processor only (master stage, no mix stage).** The plugin
  is inserted on the DAW **master bus**, where the signal is a single summed
  stereo mix. Keel's mix/balance stage needs the **separate stems** (it balances
  labeled groups relative to the vocal), and a stereo master **cannot** re-balance
  instruments (locked scope, CLAUDE.md / ADR-0001). So the plugin does the
  **master stage only**; balancing stays in the standalone tool (run on the stems
  before they enter the DAW) or in the DAW's own mixer. A "stem balancer" plugin
  is a deferred follow-on (it needs cross-track visibility a per-track insert
  can't provide).
- **Plugin GUI is distinct from — and much simpler than — the standalone GUI.**
  The standalone (`gui.py`) works on a folder of stems: file->label table +
  per-label balance faders + render mix+master. The plugin **drops** the
  file->label table and balance faders entirely and **keeps only** the master
  controls: target preset (streaming -14 / loud -10 / broadcast -16) + LUFS/TP
  fields, optional reference + glue toggle, **live LUFS/TP meters**, and the
  **Apply** button. Same `mastering.py` brain, just the master half.
- **Shell (new, C++):** loads in the DAW, draws the UI, runs **real-time
  pass-through** while driving **live LUFS / true-peak meters** (display-only, like
  the GUI's playback meters — ADR not changed), captures the program audio, and
  exposes an **Apply master** action.
- **Apply (offline):** on Apply, the shell writes the captured/bounced audio to a
  temp WAV, **shells out to the existing Python Keel engine** to master it, and
  reads the result back into the DAW. Same code as the CLI/GUI, so the master is
  **byte-identical** to `build.py` / `gui.py` output: exact -14 LUFS, -1 dBTP,
  deterministic. The DSP is **not** forked.
- **No system Python required:** the plugin bundles the already-built **frozen Keel
  engine** (the PyInstaller artifact, ADR-0021) and invokes it headlessly as a
  child process. The user installs the plugin; Python is an internal detail.
- **Live meters** in the shell use a C++ BS.1770 / true-peak implementation
  (candidate: **libebur128**, BSD). These are display-only; small differences from
  pyloudnorm are acceptable exactly as they are for the GUI's live meter. The
  authoritative numbers come from the engine's own report after Apply.
- **Production polish target: ARA2.** ARA gives a plugin whole-clip access, so the
  offline Apply can analyze and return audio with no manual bounce/export step
  (how Melodyne / SpectraLayers / VocAlign integrate). v1 can ship with a plain
  bounce-then-Apply flow; ARA is the follow-on that removes the manual step.
- **Licensing:** JUCE under its **AGPLv3** option for the open/free plugin
  (consistent — the engine is already AGPL); JUCE **Starter** (free under 20k/yr
  incl. donations) covers commercial seats until/unless revenue crosses the
  threshold, then **Indie** (USD 800 perpetual). The plugin follows the same hybrid
  product model as the GUI (ADR-0025). The **ARA SDK** (Celemony) and **VST3 SDK**
  (Steinberg) license terms must be reviewed before public distribution.

**A C++ port of the master DSP is explicitly deferred and may never happen.** It
would only be revisited if a zero-Python-runtime plugin is wanted later, and even
then it would be **validated against the Python reference** (render the same file
both ways; compare LUFS/TP; null-test), never a blind rewrite.

## Consequences

- The Python engine (`mixer.py`, `mastering.py`, `meters.py`, `recipes.py`,
  `keel.py`) is **reused, not retired** — the plugin is a third front-end on the
  one shared core, alongside the CLI and GUI. No DSP fork; the determinism and
  exact-loudness guarantees carry over unchanged.
- The new code is the C++/JUCE shell: DAW integration, UI, live meters, audio
  capture, subprocess orchestration. This adds a **C++ toolchain** to a previously
  Python-only project (MSVC 14.50 + cmake 4.2.3 + VS Community 2026 confirmed
  present on the dev machine).
- **Apply is not instantaneous** — it spawns the frozen engine and renders offline
  (a few seconds), consistent with a "print/render" workflow, not a live insert.
  This is acceptable and matches exact-LUFS plugins in the market.
- The plugin **bundles the frozen engine**, so its installer is larger and the CI
  build must produce the frozen engine first, then the plugin. (Packaging detail
  for a later ADR.)
- macOS will need its own JUCE build + the frozen engine for arm64 (matching the
  existing .dmg target, ADR-0021); code-signing / notarization is still the open
  packaging item shared with Phase 4.
- ARA adds a third-party SDK and real complexity; deferring it to a follow-on keeps
  the first plugin shippable.

## References

- Hybrid model + offline-LUFS rationale: ADR-0003 (loudness target), ADR-0005
  (clip-then-limit), ADR-0006 (oversampled true-peak).
- One shared core / don't fork the DSP: [ADR-0013](0013-keel-py-library-facade.md).
- Product/licensing model reused: [ADR-0023](0023-dual-licensing.md),
  [ADR-0025](0025-gui-noncommercial-license-and-donations.md).
- Frozen engine reused for shell-out: [ADR-0021](0021-desktop-packaging-pyinstaller.md).
- JUCE 8 EULA / tiers: <https://juce.com/legal/juce-8-licence/>,
  <https://forum.juce.com/t/revenue-limits-for-juce-tiers/61058>
- VENOM (rejected, GPLv3): <https://github.com/aszokalski/venom>
- ARA overview: <https://www.sonible.com/blog/what-is-ara/>
- libebur128 (C++ BS.1770 / true-peak, BSD): <https://github.com/jiixyj/libebur128>
- ROADMAP Phase 5.
