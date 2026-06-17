# Keel plugin (Phase 5)

A JUCE/C++ master-bus plugin for Keel — a third front-end alongside the CLI
(`build.py`) and standalone GUI (`gui.py`). It is a **self-contained real-time
master**: it runs Keel's master chain live in C++, and you deliver by exporting
from your DAW with it active. There is no offline step. See
[ADR-0029](../docs/adr/0029-plugin-self-contained-master.md) (supersedes ADR-0027).

> **DSP SYNC RULE (load-bearing).** The C++ live chain in `Source/` and
> `mastering.py` are two **disconnected** implementations of the same master
> character. Python is the reference; if you change the master math there, mirror
> it here and re-A/B. See ADR-0029 / CLAUDE.md.

## What it does

- **Master-bus processor** (stereo in == stereo out), VST3 + Standalone.
- **Live master chain (real-time, a faithful port of `mastering.py`):**
  tone (HPF 28 / low-shelf +1 dB\@110 / air +1.5 dB\@9k / glue comp -14, 1.6:1)
  -> static **Makeup** gain -> oversampled tanh soft-clip -> 4x oversampled
  true-peak limiter. You hear the Keel master and tweak it; the TP ceiling
  (-1 dBTP) is honored live, so DAW exports are TP-safe. Built from the same
  `juce::dsp` blocks pedalboard wraps, so it ports closely — but the C++ limiter is
  **not** byte-identical to pedalboard's, so it sounds *close*, validated by A/B
  not by null.
- **Loudness is approximate, set by hand.** You raise **Makeup** until the live
  LUFS meter sits at the target. The gain is **static** (not adaptive), so playback
  and a DAW bounce are identical — no intro ramp. Exact integrated LUFS is
  whole-program, so it can't be a single-pass live value; for a guaranteed exact
  -14 LUFS / -1 dBTP file, run the audio through the CLI / GUI (the Python engine).
- **Live meters (display-only):** a BS.1770-4 K-weighted momentary LUFS meter and
  a 4x-oversampled true-peak meter, reading the **chain OUTPUT** (what you hear).
- **Master-only UI** (ADR-0029): preset (streaming -14 / loud -10 / broadcast
  -16) + target LUFS (a meter reference) + TP ceiling + **Makeup** + reference/glue
  toggles + the two meters. The TP / Makeup sliders retune the live chain
  instantly. It deliberately drops the standalone GUI's file->label table and
  balance faders — a stereo master cannot re-balance instruments (ADR-0001).
- **Shared visual language** with the standalone GUI
  (`Source/KeelLookAndFeel.{h,cpp}`): the teal brand palette, Space Grotesk
  (embedded, SIL OFL), card panels, the hull mark, and the gradient LUFS /
  true-peak meters — all ported from `gui_theme.py`.

### Not done yet (next steps)

- **By-ear A/B validation** of the live master vs a `build.py` render of the same
  audio is pending (load it on the master bus, compare); expect "close," not
  identical.
- The tone-stage glue comp is **always on** in the live chain (faithful to
  `mastering.py`, where it is part of the tone stage). The UI "Bus glue" /
  "Reference" toggles are not yet wired to the live chain.
- The meters use a self-contained K-weighting (JUCE RBJ biquads), not
  `libebur128` yet — fine for a display meter; swap in later if wanted.

## Build

Requires CMake >= 3.22, Visual Studio 2026 (MSVC), git, and internet on the first
run (CMake FetchContent pulls JUCE 8.0.9).

```powershell
cd plugin
.\build.ps1                 # configure + Release build (VST3 + Standalone)
.\build.ps1 -Debug          # Debug build
.\build.ps1 -Clean          # wipe build/ first
```

Or directly:

```powershell
cmake -S . -B build -G "Visual Studio 18 2026" -A x64
cmake --build build --config Release
```

Artifacts:

- `build/KeelPlugin_artefacts/Release/VST3/Keel.vst3`
- `build/KeelPlugin_artefacts/Release/Standalone/Keel.exe`

The Standalone exe is the fastest way to sanity-check the live chain + meters with
no DAW. The VST3 loads in a DAW (Reaper is the ARA target later).

`plugin/build/` is git-ignored.

### Installing into a DAW

`COPY_PLUGIN_AFTER_BUILD` is on, so each build **auto-copies** `Keel.vst3` into
the per-user VST3 folder (no admin):

- Windows: `%LOCALAPPDATA%\Programs\Common\VST3\Keel.vst3`
- macOS:   `~/Library/Audio/Plug-Ins/VST3/Keel.vst3`

Then **rescan** in the host (Reaper: Preferences -> Plug-ins -> VST -> Re-scan).
The plugin shows as **Keel** (Felipe Carvajal Brown), category Mastering/Dynamics.

Some hosts (e.g. Mixcraft) only scan the **system** folder
`C:\Program Files\Common Files\VST3`, which needs admin. To install there, run an
elevated copy:

```powershell
Copy-Item "build\KeelPlugin_artefacts\Release\VST3\Keel.vst3" `
    "C:\Program Files\Common Files\VST3" -Recurse -Force
```

## Licensing

JUCE under its **AGPLv3** option for the open plugin (the engine is already
AGPL). JUCE **Starter** (free under USD 20k/yr, incl. donations) covers
commercial seats until revenue crosses the threshold, then **Indie** (USD 800
perpetual). Same hybrid product model as the GUI (ADR-0025). The VST3 SDK
(Steinberg) and, later, ARA SDK (Celemony) license terms must be reviewed before
public distribution.
