**Alpha** release of Keel (deterministic automix + automaster) — the desktop GUI,
and now the **Keel VST3 plugin** for your DAW.

## Downloads
- **Windows app** — `KeelSetup-<ver>.exe` (recommended installer) or `Keel.exe` (portable).
- **Windows plugin** — `Keel-VST3-windows-<ver>.zip` — unzip `Keel.vst3` into your
  VST3 folder (`%LOCALAPPDATA%\Programs\Common\VST3` or
  `C:\Program Files\Common Files\VST3`), then rescan in your DAW.
- **macOS (Apple Silicon / arm64)** — `Keel.dmg` (app). The plugin is Windows-only
  for now.

## New in this release
- **Keel VST3 plugin (preview):** a self-contained real-time master for your DAW's
  master bus — Keel's master chain runs live (tone -> Makeup -> oversampled
  soft-clip -> 4x true-peak limiter). Set **Makeup** so the loudness meter sits at
  target, then export from your DAW with it active. The true-peak ceiling is held
  live, so exports stay safe. It wears the same look as the app. For an exact
  -14 LUFS / -1 dBTP, deterministic master, use the app or CLI (the reference).

## Heads-up: these builds are unsigned
They are not yet code-signed, so the OS will warn on first launch:
- **Windows**: SmartScreen shows "Windows protected your PC" — click
  **More info -> Run anyway**.
- **macOS**: Gatekeeper blocks an unidentified developer — **right-click
  the app -> Open**, then confirm.

Signing/notarization is planned. See `ROADMAP.md` for status and
`README.md` for what Keel does.
