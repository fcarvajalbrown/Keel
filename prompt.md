# Next-agent prompt — Keel

You are picking up work on **Keel**, a deterministic automix + automaster engine
(stems in -> balanced mix + loudness-safe master out). The long-term goal is a
**standalone GUI** and a **VST/plugin**. The CLI engine is done and validated on
real-world material (see Phase 2 status below).

## Do this first, before writing any code

1. **Read these, in order:** `CLAUDE.md` (scope, locked DSP, conventions),
   `ROADMAP.md` (where we are and what's next), `README.md` (the product story).
   Do not skip them — they encode decisions already made.
2. **Locate the current phase in `ROADMAP.md`.** Phases 0-1 (engine core +
   song-agnostic standalone) are DONE. **Phase 2 (validate on real-world
   material) is IN PROGRESS** — most of it is checked off (see below); Phases 3-6
   (config/presets, GUI, VST, distribution) follow.
3. **Confirm direction with the user before proceeding.** Do not assume the next
   roadmap item is what they want today. Ask via the **interactive arrow-select
   option UI (the blue selector), not a plain-text list** — firm preference (see
   CLAUDE.md). Offer the open items below as options.

## Where Phase 2 stands (validated last session, 2026-06-15)

Ran Keel on **three real deliveries** and it held up: a Cambridge MT 18-track raw
rock kit (48 kHz), a 17-track synth-heavy multitrack (44.1 kHz), and the user's
own **5-stem pre-mixed format** (`Drums`/`Bass`/`Guitar 1`/`Guitar 2`/`Synth`).
All three auto-labeled correctly and mastered to **exactly -14.0 LUFS, 3-4 dB
under the -1.0 dBTP ceiling**, clean, no clipping. The test stems live OUTSIDE the
repo at `C:\Projects\Keel-testdata\song1|song2|song3\` (not committed).

Two real bugs surfaced and were fixed (commits `a1a99a4`, `1a18698`, `89796ce`):
- Mixed mono/stereo groups crashed the mixer -> groups are now summed to stereo
  for the loudness measurement, matching the render path.
- Per-component drum mics (kick/snare/toms/overheads) scattered to `other`
  instead of grouping as one kit -> auto-detect rewritten to **token /
  word-boundary matching** (anchored, so `oh` != `john`, `ride` != `pride`), plus
  a **`--scan` mapping review** that prints per-label counts and a `[check]`
  callout for anything in `other`.

Infra the user asked for, done:
- **Dependency vault completed** — the optional `matchering` reference-master tree
  is now vendored (commit `ed7ec5d`); verified it installs fully offline and
  imports on CPython 3.14. `vendor/` covers BOTH master paths now.
- **Venv workflow** — `setup.ps1` builds `.venv` and installs offline from
  `vendor/` (`-Online` for PyPI, `-Matchering` for the reference path). The venv
  is gitignored, rebuilt per machine.

## Since then (this session, 2026-06-16)

Shipped four listening-free items (engine still validated, all committed +
pushed, 19-test suite green):
- **Named master presets (Phase 3 DONE).** `build.py --preset NAME` picks a
  house-sound loudness profile, applied live at render over keel.json's master
  block (explicit `--lufs/--tp` still win). Shipped `streaming` (-14, default),
  `loud` (-10), `broadcast` (-16), all at -1.0 dBTP; values web-researched +
  cited (Spotify/YouTube/Tidal -14; club -10; Apple Music / AES TD1008 -16).
  `--list-presets` prints them. Master-target-only by design (a preset sets how
  loud it lands, not the balance). See `recipes.PRESETS` / `preset_master()`.
- **Bus glue wired.** The pre-existing off-by-default `mixer.mix(glue=...)`
  compressor is now reachable: keel.json `"glue": false` + `--glue/--no-glue`
  (CLI beats the mapping). Still OFF by default — the remaining call is the
  by-ear evaluate, which needs the user. No DSP change when unset.
- **Library facade (Phase 4 prep DONE).** `keel.py` is the public API
  (`import keel` -> mix/master/recipes/presets/meters). Single import surface so
  the future GUI/plugin share one core; DSP not forked.
- **Test suite.** `tests/test_engine.py` (stdlib unittest, no new dep) checks
  determinism (byte-identical), exact master LUFS under the TP ceiling, the
  group-balance invariant, the mono+stereo regression, >2ch coercion, and label
  matching. Run: `.venv\Scripts\python.exe -m unittest discover -s tests`.
- **Robustness.** `_to_stereo` handles >2 channels explicitly; build.py errors
  clearly on a missing `--stems`/`--batch` folder.
- **Desktop GUI scaffold (Phase 4 IN PROGRESS).** `gui.py` (PySide6/Qt) drives
  `import keel` (no DSP fork): drop/open a stems folder -> editable file->label
  table -> per-label balance faders (LU) -> loudness preset picker with user
  save/load (`userpresets.py`, gitignored JSON) -> optional reference + bus-glue
  toggle -> one-click mix+master in a worker thread -> post-render LUFS/TP meters
  (via meters.py) -> save/load project keel.json. Headless-smoke-tested
  (QT_QPA_PLATFORM=offscreen) end to end on song3. Toolkit decision: PySide6, not
  Kivy (Kivy has no cp314 wheels, won't install on 3.14; PySide6 is abi3 + LGPL,
  fits the commercial build). GUI deps install ONLINE via `setup.ps1 -Gui` /
  `requirements-gui.txt` -- NOT vendored (~150 MB Qt; core engine stays offline).
  Still open in Phase 4: real-time playback metering, live re-render on fader
  move.
- **Executables + CI (Phase 4).** `Keel.spec` (PyInstaller) builds a Windows
  onefile `Keel.exe` and a macOS `Keel.app`; `gui.py --selftest` lets the frozen
  app verify itself headlessly. `.github/workflows/build-app.yml` builds BOTH on
  windows-latest + macos-latest(arm64) on manual/tag trigger only (never on
  push, so no failure spam), each gated by --selftest, uploading `Keel.exe` +
  `Keel.dmg` artifacts. Validated green end-to-end via `gh` (run 27649684004,
  zero annotations; Keel.exe ~93 MB, Keel.dmg ~64 MB). macOS is arm64 only (the
  only arch with a cp314 pedalboard wheel). STILL OPEN: code-signing /
  notarization (the .app/.exe are unsigned) and a proper installer; an Intel-mac
  (macos-13 + py3.13) job if needed.
- **Commercial model (ROADMAP Phase 6).** AGPL engine stays free; the packaged
  GUI is the paid product (~USD 20) sold from a GitHub Pages static site under
  COMMERCIAL-LICENSE.md (LGPL PySide6 makes the closed build legal).

## The immediate open task: Matchering reference A/B (Phase 2)

The user chose to run a **Matchering vs. internal-master A/B on ALL THREE songs**,
then paused to do it "later." It is set up and ready:
- `matchering` is already installed in `.venv` (offline). Run build/mastering with
  `.venv\Scripts\python.exe`.
- **Still needed from the user:** mastered, full-length **WAV/FLAC reference
  track(s)** — ideally genre-matched per song (rock for song1, electronic for
  song2, their genre for song3). One reference reused across all is acceptable but
  skews the match (matchering copies the reference's tonal balance + loudness; the
  reference SETS loudness, so the -14 target is ignored on that path).
- **Plan:** for each song, master its existing `out/songN_mix.wav` through the
  reference path into a separate file (e.g. `out/songN_ref_master.wav`) so the
  internal master is kept side by side, then compare LUFS / true-peak / how hard
  each pushes and **document when internal vs. reference wins** (the open
  ROADMAP Phase 2 item). Easiest via `mastering.master(...)` directly, or
  `build.py --master-only --ref <path>` (note: `--master-only` looks for
  `<out>/<name>_mix.wav`, so reuse `--name songN` or call the module directly to
  avoid clobbering the internal master).

Other remaining Phase 2 items: **bus glue** is now wired (keel.json `"glue"` +
`--glue`) but still OFF — the open part is the by-ear evaluate (needs the user);
and `DEFAULT_BALANCE`/target tuning (so far the defaults generalized without
tuning — research-before-tweak if you change DSP).

## How the user likes to work (match this)

- **Decisions -> arrow-select UI.** Every fork, however small, through the blue
  selector. Chain calls if >4 questions. Text only if the UI is unavailable.
- **No emojis** anywhere (docs, commits, code, chat). Plain text only.
- **No AI attribution in commits/PRs** — do NOT add a `Co-Authored-By: Claude`
  trailer (saved to memory: `no-claude-coauthor`).
- **Conventional + logical commits**, one atomic change each. **Auto-push** to
  `origin` after each logical commit (don't ask first).
- **Don't hardcode delivery assumptions.** The user pushed hard on this: the
  engine must handle any stem-delivery shape (pre-mixed bus, multi-mic kit,
  doubles, unknown names -> `other`). `STEM_ALIASES` is only an editable
  auto-detect hint. Saved to memory: `engine-stays-delivery-agnostic`.
- **Research-before-tweak for DSP.** ~5 web searches + citations before changing
  the mixing/mastering approach. Do not tune DSP from memory.

## Hard guardrails (do not violate)

- Scope is **balance + master only**. No tone shaping in the mix stage, no stem
  separation, no ML, no randomness in the render path.
- Keep `mixer.py` / `mastering.py` / `meters.py` project-agnostic. No song lists,
  no fixed stem-type set, no folder assumptions.
- Locked DSP defaults: master **-14.0 LUFS / -1.0 dBTP**, internal anchor
  **-20 LUFS**. Change only deliberately, with research.
- Never hand-edit files in `out/` — build artifacts.

## Other open items (raise with the user when relevant)

- **Folder rename: DONE.** The repo now lives at `C:\Projects\Keel` (memory
  project key `C--Projects-Keel`). Memories re-saved under the new key last
  session (`no-claude-coauthor`, `engine-stays-delivery-agnostic`).
- **License:** done — AGPL-3.0 + dual commercial (`LICENSE`, per-file headers,
  `COMMERCIAL-LICENSE.md`, README section). Remaining only if desired: formal
  legal review.
- **Trademark:** "Keel" cleared initial web searches; verify formally in target
  markets before public launch.
- **GUI scaffolding (Phase 4):** keep the engine importable as a shared library so
  CLI, GUI, and plugin drive one core. Don't fork the DSP.
- **Landing assets:** tagline/elevator pitch, logo/wordmark, before/after demo
  audio (not started).

## Quick sanity check (engine still runs)

```powershell
.\setup.ps1                 # build .venv + install core engine offline from vendor/
.\.venv\Scripts\Activate.ps1
python -m py_compile recipes.py build.py mixer.py mastering.py meters.py
python build.py --help
python build.py --stems "C:\Projects\Keel-testdata\song3" --out out   # writes keel.json, renders
```

Start by reading the three docs, then ask the user (via the option UI) what this
session is for — the Matchering A/B is teed up and waiting on a reference track.
