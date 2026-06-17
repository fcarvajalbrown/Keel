# Keel plugin (Phase 5)

A JUCE/C++ master-bus plugin for Keel — a third front-end alongside the CLI
(`build.py`) and standalone GUI (`gui.py`). It runs a **live C++ master chain (a
faithful PREVIEW)** in real time, and delivers the **byte-identical master from
the Python engine on Finalize**. See
[ADR-0027](../docs/adr/0027-plugin-live-cpp-chain.md) (supersedes ADR-0026).

> **DSP SYNC RULE (load-bearing).** The C++ live chain in `Source/` and
> `mastering.py` are two **disconnected** implementations of the same master
> character. Python is the reference; if you change the master math there, mirror
> it here and re-A/B. See ADR-0027 / CLAUDE.md.

## What it does

- **Master-bus processor** (stereo in == stereo out), VST3 + Standalone.
- **Live master chain (real-time, a faithful preview of `mastering.py`):**
  tone (HPF 28 / low-shelf +1 dB\@110 / air +1.5 dB\@9k / glue comp -14, 1.6:1)
  -> Ozone-style auto makeup toward the target -> oversampled tanh soft-clip
  -> 4x oversampled true-peak limiter. You hear the Keel master and tweak it; the
  TP ceiling (-1 dBTP) is honored live. Built from the same `juce::dsp` blocks
  pedalboard wraps, so it ports closely — but the C++ limiter is **not** byte-
  identical to pedalboard's, so it sounds *close*, validated by A/B not by null.
- **Loudness is approximate live.** The auto makeup chases a slow K-weighted
  loudness estimate toward the target (whole-program exact LUFS can't be live).
  **Exact -14 LUFS / -1 dBTP is locked only on Finalize** (ADR-0027 amends
  ADR-0003 for the plugin).
- **Live meters (display-only):** a BS.1770-4 K-weighted momentary LUFS meter and
  a 4x-oversampled true-peak meter, now reading the **chain OUTPUT** (what you
  hear). The authoritative numbers come from the engine on Finalize.
- **Master-only UI** (ADR-0027): preset (streaming -14 / loud -10 / broadcast
  -16) + target LUFS + TP ceiling + reference/glue toggles + the two meters +
  **Finalize**. Moving the LUFS / TP sliders retargets the live chain instantly.
  It deliberately drops the standalone GUI's file->label table and balance
  faders — a stereo master cannot re-balance instruments (ADR-0001).

### Not done yet (next steps)

- **Finalize is a stub.** It pops an info dialog. The shipped version will bounce
  the program audio to a temp WAV, run the **bundled frozen Keel engine** as a
  child process to master it (byte-identical to `build.py` / `gui.py`: exact
  -14 LUFS, -1 dBTP, deterministic), and read the result back. No system Python
  needed.
- **By-ear A/B validation** of the live preview vs the Python master is pending
  (load it on the master bus, compare against a `build.py` render of the same
  audio); expect "close," not identical.
- The tone-stage glue comp is **always on** in the live chain (faithful to
  `mastering.py`, where it is part of the tone stage). The UI "Bus glue" toggle is
  not yet wired to the live chain — it will gate the Finalize path.
- **ARA2** (whole-clip access, no manual bounce) is the production polish.
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
