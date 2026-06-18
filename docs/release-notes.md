**Beta** release of Keel (deterministic automix + automaster) — the desktop GUI
and the **Keel VST3 plugin** for your DAW, now hardened and built together by CI.

## Downloads
- **Windows app** — `KeelSetup-<ver>.exe` (recommended installer) or `Keel.exe` (portable).
- **Windows plugin** — `Keel-VST3-windows-<ver>.zip` — unzip `Keel.vst3` into your
  VST3 folder (`%LOCALAPPDATA%\Programs\Common\VST3` or
  `C:\Program Files\Common Files\VST3`), then rescan in your DAW.
- **macOS (Apple Silicon / arm64)** — `Keel.dmg` (app). The plugin is Windows-only
  for now (a macOS plugin build is the next milestone).

## New in this release
- **More instruments + a real instrument dropdown.** The known set now also covers
  **piano, organ/keys, backing vocals, and aux percussion** on top of
  vocals/drums/bass/guitar/synth — each balanced as its own group at a sensible
  default level. In the app, each file's label is now an **editable instrument
  dropdown**: a generically-named stem like `track1.wav` is one click to assign as
  guitar, piano, etc. (custom labels still allowed). Aux percussion and organ/keys
  now group apart from the drum kit and the synth.
- **Tougher on bad input.** Corrupt/unreadable audio and a malformed (hand-edited)
  `keel.json` now produce a clear message instead of a crash, the `keel.json` is
  never silently overwritten, NaN/Inf samples are handled cleanly, and a `--batch`
  run reports a bad folder and carries on.
- **Trustworthy builds.** The test suite now runs on Windows + macOS as a release
  gate, and the **plugin is built and smoke-validated in CI** — a single release
  now ships the app and the plugin together, automatically.

## Heads-up: these builds are unsigned
They are not yet code-signed, so the OS will warn on first launch:
- **Windows**: SmartScreen shows "Windows protected your PC" — click
  **More info -> Run anyway**.
- **macOS**: Gatekeeper blocks an unidentified developer — **right-click
  the app -> Open**, then confirm.

Signing/notarization is the v1.0.0 gate. See `ROADMAP.md` for status and
`README.md` for what Keel does.
