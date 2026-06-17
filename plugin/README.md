# Keel plugin (Phase 5 spike)

A **thin JUCE/C++ shell** for Keel's master stage — a third front-end on the one
shared core, alongside the CLI (`build.py`) and standalone GUI (`gui.py`). It is
**not** a DSP fork. See [ADR-0026](../docs/adr/0026-plugin-architecture-juce-shell.md).

## What this spike is

The goal of this spike is to retire the biggest risk — that a JUCE + CMake +
MSVC plugin builds and loads at all on this machine — before investing in the
real Apply path. So it does the minimum that proves the architecture:

- **Master-bus processor** (stereo in == stereo out), VST3 + Standalone.
- **Real-time pass-through.** The audio is not altered; mastering is offline.
- **Live meters (display-only):** a BS.1770-4 K-weighted momentary LUFS meter and
  a 4x-oversampled true-peak meter. Small differences from the engine's
  `meters.py` are acceptable here, exactly as for the GUI's playback meters; the
  authoritative numbers come from the engine after Apply.
- **Master-only UI** (ADR-0026): preset (streaming -14 / loud -10 / broadcast
  -16) + target LUFS + TP ceiling + reference/glue toggles + the two meters +
  **Apply**. It deliberately drops the standalone GUI's file->label table and
  balance faders — a stereo master cannot re-balance instruments (ADR-0001).

### Not in this spike (next steps)

- **Apply is a stub.** It pops an info dialog. The shipped version will bounce the
  program audio to a temp WAV, run the **bundled frozen Keel engine** as a child
  process to master it (byte-identical to `build.py` / `gui.py`: exact -14 LUFS,
  -1 dBTP, deterministic), and read the result back. No system Python needed.
- **ARA2** (whole-clip access, no manual bounce) is the production polish.
- Reference/glue toggles are wired as parameters but not yet acted on.
- The meter uses a self-contained K-weighting (JUCE RBJ biquads), not
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

The Standalone exe is the fastest way to sanity-check pass-through + meters with
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
