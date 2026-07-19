**Beta** release of Keel (deterministic automix + automaster). This one is a
**plugin** release — "Plugin depth". It closes the plugin's credibility gap
(Makeup was aimed at a *momentary* meter while streaming normalizes on
*integrated* LUFS) and makes it trustworthy and pro-grade: real BS.1770
integrated + short-term meters, LRA, loudness + gain-reduction history graphs, a
true-peak peak-hold, and a loudness-matched A/B — plus the quality-of-life a DAW
user expects (hiDPI resize, undo/redo, user presets, tooltips, accessibility, a
plugin-only oversampling selector). No master tone math changed anywhere, so the
plugin and the CLI/GUI master stay in step.

## Downloads
- **Windows app** — `KeelSetup-<ver>.exe` (recommended installer) or `Keel.exe` (portable).
- **macOS app (Apple Silicon / arm64)** — `Keel.dmg`.
- **Windows plugin** — `Keel-VST3-windows-<ver>.zip` — unzip `Keel.vst3` into your
  VST3 folder (`%LOCALAPPDATA%\Programs\Common\VST3` or
  `C:\Program Files\Common Files\VST3`), then rescan in your DAW.
- **macOS plugin (Apple Silicon / arm64)** — `Keel-plugins-macos-<ver>.zip` —
  contains `Keel.vst3` and `Keel.component` (AU). Drop them into
  `~/Library/Audio/Plug-Ins/VST3` and `~/Library/Audio/Plug-Ins/Components`, then
  rescan (Logic Pro / GarageBand use the AU).

## New in this release
### Plugin metering (the credibility fix)
- **Integrated + short-term LUFS meters.** The plugin now shows real BS.1770-4
  **integrated** loudness as the primary aimed meter — the number streaming
  services normalize on — with short-term + momentary alongside and a **Reset**.
  Previously Makeup was steered against a momentary meter, so users aimed at the
  wrong number.
- **Loudness range (LRA)** readout (EBU R128), plus a scrolling **loudness-history
  graph** and a **gain-reduction history graph** so consistency and how hard the
  limiter works are visible, not guessed.
- **True-peak peak-hold** — a latched maximum on the TP meter (red once it ever
  crossed the ceiling), so a stray overshoot can't scroll away unseen.
- **Loudness-matched A/B bypass** — audition the dry input gain-matched to the
  master's loudness, so the comparison exposes *character*, not the loudness lift.

### Plugin quality-of-life
- **hiDPI resize** (aspect-locked, crisp vector scaling — no OpenGL), **undo/redo**
  (buttons + Ctrl+Z/Y), **user presets** (save/recall full snapshots), **tooltips**
  + a **first-run note** explaining the deliver-by-DAW-export workflow, cleaner
  **host-automation** (the preset macro now applies under automation with no editor
  open; params carry unit labels), and **accessibility** labels + screen-reader
  meter values.
- **Oversampling-quality selector** (2x / 4x / 8x) on the plugin's live clip/limiter
  — trade CPU vs alias suppression. The true-peak *meter* stays fixed 4x, and the
  byte-identical CLI/GUI path is unchanged, so determinism holds.

### Standalone GUI mirror
- **Loudness range (LRA)** now appears in the post-render dynamics readout alongside
  PLR / PSR / phase-correlation (and in `out/REPORT.md`).
- **Loudness-matched A/B** in the GUI: audition the pre-master mix gain-matched to
  the master's loudness, switching live during playback.

## Heads-up: these builds are unsigned
They are not yet code-signed, so the OS will warn on first launch:
- **Windows**: SmartScreen shows "Windows protected your PC" — click
  **More info -> Run anyway**.
- **macOS**: Gatekeeper blocks an unidentified developer — **right-click
  the app (or plugin) -> Open**, then confirm.

Signing/notarization is the v1.0.0 gate. See `ROADMAP.md` for status and
`README.md` for what Keel does.
