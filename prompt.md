# Next-agent prompt — Keel

You are picking up work on **Keel**, a deterministic automix + automaster engine
(stems in -> balanced mix + loudness-safe master out). The long-term goal is a
**standalone GUI** and a **VST/plugin**. The CLI engine is done and validated on
real-world material; the GUI scaffold + cross-platform builds now exist too.

## >>> START HERE — immediate next task

**Phase 4 GUI polish is DONE** (shipped 2026-06-17, commits on `main`):
1. **Real-time playback metering** — `gui.py` now has a "Play master" button
   that streams the rendered master to the audio device via QtMultimedia
   QAudioSink (Int16 push mode) and drives the LUFS / true-peak meters live off
   the actual playback position, measuring a trailing 3 s window with the
   engine's own `meters.py` math. Throttled (~150 ms) meter recompute; guarded
   import + `available()` device gate so headless/no-device (incl. `--selftest`)
   degrades to a disabled button. Display-only — render path stays deterministic.
2. **Live re-render on fader move** — a default-off "Live preview" checkbox; a
   fader settling (re)arms a single-shot debounce timer that re-renders the full
   mix + master via the existing RenderWorker, coalescing moves made mid-render.
   Faders change level balance only (ADR-0001 scope lock honored).

Both validated headlessly (`--selftest` green; playback verified emitting live
reads against a rendered song3 master). Confirm direction with the user via the
blue option UI before the next task — candidates, none started:
- **Phase 4 packaging:** code-signing / notarization (needs the publication fee
  paid first) + a proper installer. The .exe/.app build green but unsigned.
- **Phase 6 landing page:** GitHub Pages static site (tagline, demo, checkout).
- **Phase 5 VST/plugin:** the next big build.

## Before writing any code

1. **Read these, in order:** `CLAUDE.md` (scope, locked DSP, conventions),
   `ROADMAP.md` (phases + status), `docs/adr/` (the decision records — *why*
   things are the way they are), `README.md` (the product story). Do not skip
   them — they encode decisions already made.
2. **Locate the current phase in `ROADMAP.md`.** DONE: Phase 0-1 (engine core +
   song-agnostic standalone), Phase 3 (presets/config). IN PROGRESS: Phase 2
   (validate — DONE this session) and **Phase 4
   (GUI — scaffold + executables + CI + polish done; only code-signing /
   installer remain, see START HERE)**.
   Phases 5-6 (VST, distribution) follow.
3. **Confirm direction with the user before proceeding.** Ask via the
   **interactive arrow-select option UI (the blue selector), not a plain-text
   list** — firm preference (see CLAUDE.md).

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
  Phase 4 GUI polish (real-time playback metering + live re-render on fader
  move) shipped 2026-06-17 — see START HERE; only code-signing / installer left.
- **Executables + CI (Phase 4).** `Keel.spec` (PyInstaller) builds a Windows
  onefile `Keel.exe` and a macOS `Keel.app`; `gui.py --selftest` lets the frozen
  app verify itself headlessly. `.github/workflows/build-app.yml` builds BOTH on
  windows-latest + macos-latest(arm64) on manual/tag trigger only (never on
  push, so no failure spam), each gated by --selftest, uploading `Keel.exe` +
  `Keel.dmg` artifacts. Validated green end-to-end via `gh` (run 27649684004,
  zero annotations; Keel.exe ~93 MB, Keel.dmg ~64 MB). macOS is arm64 only (the
  only arch with a cp314 pedalboard wheel). STILL OPEN: code-signing /
  notarization (the .app/.exe are unsigned) and a proper installer; an Intel-mac
  (macos-13 + py3.13) job if needed. User is on an **Apple Silicon M4** (arm64),
  so the existing arm64 .dmg is correct — no Intel job needed. User said they'll
  **pay the publication/signing fee later**; unsigned builds are fine for testing.
- **ADRs backfilled.** `docs/adr/` now holds 24 Nygard-format decision records
  (+ index) covering every load-bearing decision (DSP locks, scope, engine
  behaviour, toolkit, licensing, packaging, CI, distribution). When a decision
  changes, add a superseding ADR — don't silently reverse one.
- **Commercial model (ROADMAP Phase 6).** AGPL engine stays free; the packaged
  GUI is the paid product (~USD 20) sold from a GitHub Pages static site under
  COMMERCIAL-LICENSE.md (LGPL PySide6 makes the closed build legal).

## Phase 2 tail — wrapped up (2026-06-17)

Closed out the small open validation items (decisions made with the user):
- **Balance / target tuning — CLOSED, no change.** `DEFAULT_BALANCE` and the
  -14 LUFS target generalized across all three real deliveries with no tuning;
  left unchanged by decision (any change needs fresh research-before-tweak).
- **Dither — CLOSED, not needed.** 24-bit in/out throughout. Documented future
  hook: add TPDF dither only if a sub-24-bit export path is ever introduced.
- **Matchering reference A/B — DROPPED** (user is wary of references; tastes
  differ). The optional reference-master path REMAINS an opt-in GUI/CLI feature
  (ADR-0009) — blank reference = Keel's default internal master; pick a file =
  match it via Matchering, that render only. The GUI now spells this out
  (placeholder + tooltip). No formal internal-vs-reference benchmark will be run.
- **Bus glue — CLOSED, stays OFF.** Wired (keel.json `glue` + `--glue` + GUI
  toggle), OFF by default (ADR-0015). Song3 A/B rendered (both at -14.0 LUFS /
  -4.08 dBTP); the user listened and judged the two ~identical, confirming glue
  is inaudible on already-mixed-ready stems. Kept only as an opt-in escape hatch.

With this, **Phase 2 is DONE** — every validation item is resolved or dropped.

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
