**Beta** release of Keel (deterministic automix + automaster) — the desktop GUI
and the **Keel plugin**, now on **Windows and macOS**, built together by CI. This
release closes the plugin's parity gap: a macOS plugin (VST3 + AU), a wired
Bus-glue control, and a reference loudness/peak readout.

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
- **macOS plugin — VST3 + Audio Unit.** The plugin now builds for macOS alongside
  Windows, including an **AU** for Logic Pro and GarageBand. The same self-contained
  live master chain runs on every platform; both formats are built and
  smoke-validated (pluginval) in CI, so one release ships the Windows and macOS
  plugins together with the apps.
- **Reference loudness/peak readout.** Load a track you admire and the plugin
  measures its **integrated LUFS + true-peak** — offline, once, on a background
  thread — and shows them next to the live master meters, so you can aim the Makeup
  gain at a real target. It's measured with libebur128 (canonical ITU-R BS.1770),
  so the numbers line up with the CLI/GUI. This is a passive readout, **not** a live
  match — the spectral/reference match stays the offline path in the CLI/GUI.
- **Bus-glue toggle, wired.** The plugin's Bus-glue control now actually gates the
  master glue compressor (default **on**, so the out-of-box master still matches the
  CLI/GUI); turning it off is a labelled, plugin-only deviation.

## Heads-up: these builds are unsigned
They are not yet code-signed, so the OS will warn on first launch:
- **Windows**: SmartScreen shows "Windows protected your PC" — click
  **More info -> Run anyway**.
- **macOS**: Gatekeeper blocks an unidentified developer — **right-click
  the app (or plugin) -> Open**, then confirm.

Signing/notarization is the v1.0.0 gate. See `ROADMAP.md` for status and
`README.md` for what Keel does.
