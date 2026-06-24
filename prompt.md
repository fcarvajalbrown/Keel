# Next-agent prompt — Keel

You are picking up work on **Keel**, a deterministic automix + automaster engine
(stems in -> balanced mix + loudness-safe master out). The long-term goal is a
**standalone GUI** and a **VST/plugin**. The CLI engine is done and validated on
real-world material; the GUI scaffold + cross-platform builds now exist too.

## >>> START HERE — immediate next task

**This session (2026-06-22) — `v0.5` started + roadmap restructured.** Shipped the
first `v0.5.0-beta` item: the **plugin Bus-glue toggle is now wired** (commit
`31b736e`) — it gates the master glue comp, default ON so the out-of-box master
still matches `mastering.py` (DSP SYNC honoured, no Python change), OFF is a
plugin-only deviation. Then a big planning pass (all in `ROADMAP.md`, ADRs
`0030-0034`): **approved a new `v0.7.0-beta` "Delivery & metering depth"**
milestone; resolved the post-1.0 DSP forks (kept stereo-width; dropped ADAA, drive
macro, linear-phase); moved **ARA2 -> non-goals**; planned **v2.0 reach**
(Android -> iOS -> web, web is "maybe"; mobile = approximate C++ chain, web =
server-side Python for exact spec; **no Apple-Intelligence/LLM** — that's a
separate repo); and made three scope carve-outs (a single **broadband master tilt
knob** post-1.0; a **plugin-only oversampling selector**; **encoded export**
MP3/OGG/FLAC/AAC). Read `ROADMAP.md` + ADRs 0030-0034 for the why.

**This session (2026-06-23) — Reference control resolved (ADR-0035).** The dead
plugin `reference` toggle is replaced with a **passive reference readout**: load a
file → it is measured once, offline, on a background thread → its **integrated
LUFS (BS.1770-4 gated) + true-peak (4x oversampled)** show next to the live meters.
No live ML/spectral match (that stays the offline Matchering path, ADR-0009); the
`reference` *param* is gone, the file path persists in the APVTS state tree and is
re-measured on project load. Metering/UI only — **no DSP-master change, no DSP
SYNC** needed. VST3 rebuilt green (zero warnings) + auto-installed; **by-ear/by-eye
check is the user's.** See `plugin/Source/PluginProcessor.cpp`
(`measureReferenceStats`/`loadReference`) + `PluginEditor.cpp`.

**This session (2026-06-23, part 2) — storage hygiene + macOS plugin build.**
Two things shipped:
- **Release-asset pruning (commit `7c9c533`).** GitHub storage was filling up:
  four prereleases each carried ~300 MB of binaries (~1.2 GB total; Actions
  artifacts/caches were already 0). Stripped the assets off the two oldest
  prereleases now (~600 MB freed) **and** added an auto-prune step to the `release`
  job — after publishing, it keeps downloadable assets on only the **newest two**
  prereleases and strips the rest, **keeping each release's notes + git tag** (only
  the heavy binaries go). So this self-cleans on every future tag.
- **macOS plugin build (VST3 + AU) (commit `1435851`).** The CI `plugin` job is now
  a windows/macos matrix. macOS configures with the **Xcode generator**, builds
  **VST3 + AU** (AU is a macOS-only JUCE wrapper added in `plugin/CMakeLists.txt` —
  same processor, **no DSP change, no DSP SYNC**), pluginval-smoke-tests both
  (the AU via its installed `.component`), and packages
  `Keel-plugins-macos-<ver>.zip` which the release job attaches. *Validated
  locally (CMake configures on Windows, YAML parses) but **NOT yet run on a real
  Mac runner** — the first green `macos-latest` run is the proof still owed.*

**Remaining `v0.5.0-beta` items (the live next task):** (1) **Verify the macOS
plugin build** on a real Mac runner (a `workflow_dispatch` run, or just let the
next `v*` tag prove it — note macOS runner minutes bill ~10x). (2) **by-ear A/B**
sign-off — user task. (3) optional libebur128 meter for tighter parity. Confirm
direction via the blue option UI first.

**Latest release: `v0.4.0-beta` (2026-06-18, all on `main`)** — Harden & CI. The
test suite is now a CI release gate (Win + macOS), and the **VST3 plugin is built
+ pluginval-smoke-tested in CI**, so ONE `v*` tag builds and attaches GUI + plugin
together (no more manual plugin build). Also in 0.4: graceful degradation on bad
input (corrupt audio / malformed keel.json / NaN / silent) + edge-case tests, and
an expanded instrument set (piano, organ/keys, backing vocals, aux percussion)
with an editable instrument dropdown in the GUI. Assets: `KeelSetup-0.4.0.exe`,
`Keel.exe`, `Keel.dmg`, `Keel-VST3-windows-0.4.0.zip` — all built+attached by CI.
Lineage: `v0.1.0-alpha` (engine + GUI scaffold + CI) -> `v0.2.0-alpha` (GUI restyle)
-> `v0.3.0-alpha` (plugin) -> `v0.4.0-beta` (harden & CI). Earlier 0.3.0 context:
the plugin then was built locally and attached by hand; that is now automated.
Earlier launch context below (still on `main`):
- **Release `v0.1.0-alpha`** — a GitHub *prerelease* with `KeelSetup-0.1.0.exe`
  (Windows installer), `Keel.exe` (portable), `Keel.dmg` (macOS arm64). CI
  (`build-app.yml`) now builds AND publishes the prerelease on a `v*` tag (the
  `release` job downloads artifacts + `gh release create --prerelease`).
- **Windows installer** — `installer/keel.iss` (Inno Setup) wraps the onefile
  `Keel.exe`; built in CI, uploaded as `Keel-windows-installer`. Unsigned (UX
  only; does NOT remove the SmartScreen warning — that still needs signing).
- **Licensing/funding model changed (ADR-0025, supersedes ADR-0024):** engine
  stays AGPL-3.0; the **GUI is now free** for non-commercial + individual
  musicians (PolyForm Noncommercial + extra grant, `LICENSE-NONCOMMERCIAL.md`), funded by
  **donations** (PayPal `fcarvajalbrown@protonmail.com`, `.github/FUNDING.yml`).
  **Commercial license USD 20 one-time per seat** (`COMMERCIAL-LICENSE.md`) only
  for business/redistribution. GUI per-file headers + installer LicenseFile
  updated.
- **README** — black-bg header logo (`scripts/make_readme_header.py`), big direct
  Windows download button -> the installer asset, centered badges, Buy-me-a-coffee
  PayPal button, Support + License sections. **`README.es.md`** added (Spanish,
  core translation) with an English/Español toggle on both. NOTE: README.es is a
  *condensed* translation — it omits the does/doesn't table, full keel.json
  schema, presets table, project structure, library/tests/GUI-build sections.
  Offer to expand it to full parity.
- **Repo SEO** — 20 researched topics + keyword-front-loaded description + website
  -> releases page (set via `gh repo edit`).
- **Instagram launch kit** — `scripts/make_launch_video.py` renders a ~19 s 9:16
  seamless-loop video (logo reveal -> stems-to-master -> loudness to -14.0 LUFS
  -> download card -> reversed-loudness outro -> fade to black) as BOTH
  `assets/keel-launch.mp4` (1080x1920) and `assets/keel-launch.gif` (preview).
  `scripts/make_launch_audio.py` cuts a length-matched audio bed from
  `out/song3_master.wav` (the user's OWN material — safe to publish; song1/2 and
  cambridge are third-party) with a loudness ramp+fade synced to the visual. A
  muxed `out/keel-launch-final.mp4` (video+audio, post-ready) is generated via
  imageio-ffmpeg. Spanish caption + hashtags in `docs/social/keel-instagram-launch.md`.
  `out/` audio/video are gitignored (not committed). The asset generators are
  tracked tools; rerunning them costs no Claude tokens.

## Phase 5 plugin — SELF-CONTAINED real-time master (2026-06-17, ADR-0029)

History: ADR-0026 (offline shell-out) -> ADR-0027 (live C++ preview + Python
**Finalize** for the exact-loudness file) -> **ADR-0029 (current): drop Finalize;
the plugin is a self-contained real-time master.** The user observed that the live
chain already masters and a DAW export bakes it in, so the offline Finalize was
redundant; and for streaming, services re-normalize loudness anyway while the TP
ceiling — the part that matters — is already enforced live by the limiter.
- **Live (C++), faithful port of `mastering.py`:** tone (HPF 28 / low-shelf +1\@110
  / air +1.5\@9k / glue comp -14,1.6:1) -> static **Makeup** gain -> oversampled
  tanh soft-clip -> 4x oversampled true-peak limiter. You hear the Keel master and
  tweak it; meters read the OUTPUT. Built from the same `juce::dsp` blocks
  pedalboard wraps (close, but the C++ limiter won't null pedalboard's).
- **Loudness = approximate, MANUAL.** A **static** Makeup gain (param `makeup`,
  -12..+24 dB) drives the chain; the user raises it until the live LUFS meter sits
  at target. Static (not adaptive) so playback and a DAW bounce are identical — no
  intro ramp. `lufs`/preset is now just the meter's target reference. TP ceiling
  enforced live -> exports are TP-safe.
- **Delivery = DAW export** with the plugin active. **No Finalize, no bundled
  engine, no shell-out.** Exact -14 LUFS / -1 dBTP byte-identical files remain
  available only via the **CLI/GUI** (the Python engine) for anyone who needs a
  guaranteed spec. Amends ADR-0003 + ADR-0013 for the plugin.
- **>>> DSP SYNC RULE (load-bearing, in CLAUDE.md):** the C++ chain and
  `mastering.py` are **two disconnected impls of the same master character.** Any
  change to the Python master math (`mastering.py`, `recipes.DEFAULT_MASTER` /
  `PRESETS`, -20 LUFS anchor, -14/-1 dBTP) **must be mirrored into the C++ chain**
  (`plugin/Source/`) and re-A/B'd, or the plugin drifts from the CLI/GUI master.
- **Scope unchanged:** master-bus only (a stereo master can't re-balance, ADR-0001);
  UI simpler than `gui.py` (no file->label table / balance faders — preset / LUFS
  ref / TP / Makeup / reference / glue + the two meters). Licensing unchanged (JUCE
  AGPLv3 / Starter; review VST3 SDK terms).

**>>> STATE (on `main`, 2026-06-17).** `plugin/` builds green (VST3 + Standalone,
JUCE 8.0.9, MSVC 14.50 / VS 2026 / CMake 4.2.3, zero warnings), **auto-installs**
to `%LOCALAPPDATA%\Programs\Common\VST3`, loaded + confirmed in Mixcraft. The live
chain is ported and the Finalize stub is **removed** (now self-contained per
ADR-0029); Makeup knob added. Build/iterate via `plugin\build.ps1`; details in
`plugin/README.md`.

**>>> VISUAL LANGUAGE MATCHED (2026-06-17).** The plugin UI now wears the
standalone's look (`plugin/Source/KeelLookAndFeel.{h,cpp}`): the teal palette
(ported from `gui_theme.COLORS`), Space Grotesk embedded via JUCE binary data
(`assets/fonts/`, `juce_add_binary_data`), a `KeelLookAndFeel` (teal sliders /
toggles / combo), the `HullMark` logo and the gradient `Meter` (title + big
readout + target/ceiling ticks) both ported from `gui_theme.py`, and card panels.
Build clean, zero warnings. **By-ear + by-eye check is the user's** (load it,
confirm the look reads right and the master sounds right).

**>>> NEXT TASKS — the road to 1.0 is now staged (see `ROADMAP.md`).** The
forward roadmap was restructured (2026-06-17) from open-ended phases into version
milestones: `v0.4.0-beta` (Harden & CI) -> `v0.5.0-beta` (Plugin parity +
cross-platform) -> `v0.6.0-beta` (Go-to-market) -> `v1.0.0` (sign + freeze +
stamp). Decisions behind the shape (confirmed with the user): 1.0 =
**feature-complete + hardened**; plugin reaches **full parity (toggles wired) +
macOS build**; **1.0 ships signed** (signing is the LAST gate but it does gate the
1.0 stamp); cadence = **staged betas**. Code-signing depends on the publication
fee; nothing before `v1.0.0` does.

**`v0.4.0-beta` — Harden & CI — SHIPPED (2026-06-18).** (Historical detail; the
live next task is the remaining `v0.5` items in the START HERE block at the top.)
All four items below landed:
1. Run the `tests/` unittest suite in CI as a release gate (Win + macOS). DONE.
2. Build the **plugin in CI** (Windows VST3) + auto-attach to the release. DONE
   (pluginval smoke-tested; one `v*` tag ships GUI + plugin together).
3. **Edge-case tests — DONE (2026-06-17).** The engine now degrades gracefully:
   NaN/Inf samples sanitized to silence at load (`mixer._load` /
   `mastering._internal_master`); a corrupt/unreadable audio file and a malformed
   hand-edited `keel.json` raise clear user-facing errors (the json is left
   intact — delete it to re-detect); `build.main` reports a bad job and carries on
   in `--batch`. New tests cover silent/NaN/corrupt audio, samplerate mismatch,
   malformed+missing keel.json, and a `--batch` integration run.
4. Wire the GUI `--selftest` + a plugin smoke check into CI as gates. DONE.

**Also shipped this session (2026-06-17): expanded instrument set + GUI dropdown.**
The known set now covers **piano, organ/keys, backing vocals, aux percussion** on
top of vocals/drums/bass/guitar/synth — each its own balance group with a
research-backed default level (`backing -4`, `piano -4`, `keys -5`, `perc -8` LU
vs the vocal anchor; vocals stays 0 = the reference). Aux perc (`tamb/shaker/
conga/...`) now groups **apart from the kit**, and organ/keys **apart from synth**
(their aliases were moved out of `drums`/`synth`). The GUI's file→label field is
now an **editable instrument dropdown** sourced from one canonical list
(`recipes.KNOWN_LABELS`, re-exported via `keel`) so the UI and engine can't drift;
custom labels are still typeable (delivery-agnostic). Suite **19 → 39**, green.
No plugin/DSP-master change (labels are mix-stage only), so no DSP SYNC needed.

Then `v0.5.0-beta` (wire the Bus-glue + Reference toggles into the live C++ chain
-- honour the DSP SYNC RULE; macOS VST3/AU in CI; by-ear A/B) and `v0.6.0-beta`
(landing page, donation + commercial checkout, trademark, `README.es` parity).

**RESOLVED (2026-06-23, ADR-0035):** the plugin's **Reference toggle** open call is
closed — it became a passive reference loudness/peak readout (load a file → offline
integrated-LUFS + true-peak readout next to the live meters), not a live match. A
live spectral match stays the offline Matchering path (ADR-0009).

## Before writing any code

1. **Read these, in order:** `CLAUDE.md` (scope, locked DSP, conventions),
   `ROADMAP.md` (phases + status), `docs/adr/` (the decision records — *why*
   things are the way they are), `README.md` (the product story). Do not skip
   them — they encode decisions already made.
2. **Locate the current milestone in `ROADMAP.md`.** The roadmap is now staged by
   version, not phase. SHIPPED through `v0.3.0-alpha`: engine core, song-agnostic
   CLI, real-world validation, presets/config, the desktop GUI (unsigned), and the
   first VST3 plugin (Windows, built locally). NEXT: `v0.4.0-beta` (Harden & CI),
   then `v0.5.0-beta` (plugin parity + macOS), `v0.6.0-beta` (go-to-market),
   `v1.0.0` (sign + freeze + stamp). See "Road to 1.0" in `ROADMAP.md`.
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
- **Licensing/funding model (ROADMAP Phase 6, ADR-0025).** Hybrid: the **engine
  stays AGPL-3.0**; the **GUI is free** for non-commercial use and for individual
  musicians making/selling their own music (PolyForm Noncommercial + an extra
  grant, `LICENSE-NONCOMMERCIAL.md`), funded by **donations** (PayPal + GitHub Sponsor via
  `.github/FUNDING.yml`). A **commercial license** (`COMMERCIAL-LICENSE.md`),
  **USD 20 one-time per seat**, is required only for business/redistribution use.
  Supersedes the old paid-GUI plan (ADR-0024). Still TODO: stand up the donate /
  commercial-checkout links on the landing page.

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
- **License:** done — hybrid (ADR-0025): engine AGPL-3.0 (`LICENSE`); GUI free
  non-commercial via PolyForm + grant (`LICENSE-NONCOMMERCIAL.md`, per-file headers on
  gui.py/userpresets.py); commercial USD 20/seat (`COMMERCIAL-LICENSE.md`);
  donations (README + `.github/FUNDING.yml`). Remaining only if desired: formal
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
