**Beta** release of Keel (deterministic automix + automaster). This one is an
**engine** release — "Delivery & metering depth". It turns Keel's loudness/true-
peak-safe promise into a *measured guarantee* on every render, and adds the export
formats and multi-target/album workflows a musician actually delivers with. No
master tone math changed, so the plugin and the CLI/GUI master stay in step.

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
- **PASS/FAIL compliance stamp + dynamics meters.** Every master in `out/REPORT.md`
  now carries a PASS/FAIL verdict (loudness within tolerance of target, true-peak
  at/under the ceiling) plus **PLR** (peak-to-loudness), **PSR** (peak-to-short-term)
  and **stereo phase-correlation** — pure arithmetic on values Keel already measures.
- **Encoded delivery formats** — `--format flac,mp3,ogg,aac`. FLAC/MP3/OGG go
  through libsndfile (offline, no extra tool); AAC uses ffmpeg if present. FLAC is
  bit-exact; the lossy formats are deterministic given the encoder version.
- **Post-codec true-peak gate.** Each encoded file is decoded and re-metered, and
  its post-codec true-peak graded PASS/WARN/FAIL against the ceiling — so "we leave
  headroom for lossy transcoding" is auditable, not a claim. Advisory only; it never
  reshapes the master.
- **Multi-target one-pass export** — `--targets streaming,-16,loud` renders one
  master per target in a single pass, each re-running the chain so every file is
  genuinely at-spec, in its own file.
- **Seeded dither for sub-32-bit export** — `--bit-depth 16 --dither tpdf` (or
  `shaped`). TPDF dither removes quantization distortion when going to 16/24-bit,
  and the PRNG is seeded so output stays deterministic (same stems + recipe + seed
  = identical file).
- **Loudness-keyed true-peak ceiling** — opt-in `--auto-tp` follows the target
  (-14 → -1, -9 → -2 dBTP); an explicit `--tp` still wins. Off by default.
- **Album loudness-consistency mode** — `--album` (with `--batch`) preserves the
  intended loudness differences between tracks instead of flattening every track to
  the same LUFS, while the album mean lands on target.
- **Deterministic reference-loudness match** — `--match-loudness ref.wav` measures
  a reference's integrated LUFS and uses it as the target (no ML/spectral match;
  the spectral match stays the offline Matchering path).

## Heads-up: these builds are unsigned
They are not yet code-signed, so the OS will warn on first launch:
- **Windows**: SmartScreen shows "Windows protected your PC" — click
  **More info -> Run anyway**.
- **macOS**: Gatekeeper blocks an unidentified developer — **right-click
  the app (or plugin) -> Open**, then confirm.

Signing/notarization is the v1.0.0 gate. See `ROADMAP.md` for status and
`README.md` for what Keel does.
