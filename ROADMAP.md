# Keel — roadmap

The mission: take Keel from a validated command-line engine to a tool **any
musician** can use — a standalone GUI and a DAW plugin — without compromising the
deterministic, transparent core.

Scope stays deliberately narrow: **balanced mix + competitive, safe master** of
already-FX-printed stems. Keel is not a full mixing console, a stem separator, or
a tone-shaping suite. See "Non-goals" at the bottom.

## Status legend
`[ ]` todo  `[~]` in progress  `[x]` done

---

## Phase 0 — Engine core (DONE)
- [x] Modules: `recipes.py` (data), `mixer.py` / `mastering.py` / `meters.py`
      (engine), `build.py` (CLI), `out/`, `references/`.
- [x] `requirements.txt` + vendored offline wheels (`vendor/`).
- [x] Loudness-balancing mixer (per-stem LUFS -> relative balance -> pan -> sum),
      tone processing OFF by default (stems are pre-treated).
- [x] Group handling for multi-file delivery (2 guitars / 2 vocals balanced as a
      group; printed image preserved; optional `spread` for dry dual-tracks).
- [x] **Real true-peak meter + limiter:** 4x polyphase-FIR oversampling
      (scipy `resample_poly`, Kaiser beta 12), master chain runs an oversampled
      soft-clip -> oversampled true-peak limiter. Research-cited (BS.1770-4,
      clipper-then-limiter, ISP/oversampling). Validated: at -14 LUFS it barely
      limits, leaving ~3-4 dB true-peak headroom. Graceful fallback if scipy is
      absent.
- [x] Mastering: internal LUFS+limiter chain AND optional Matchering reference path.
- [x] `out/REPORT.md` QC sheet on every run (per-stem balance + master LUFS/dBTP
      vs. target).

## Phase 1 — Song-agnostic standalone tool (DONE)
- [x] Decouple the engine from any single project: removed the hardcoded song
      list, no `../song{N}/` assumptions.
- [x] `build.py` CLI: `--stems <dir> --out <dir> [--name --lufs --tp --ref
      --mix-only --master-only]` masters any folder of named stems.
- [x] `--batch <dir>` mode: mix+master every subfolder that contains stems.
- [x] `recipes.py` reduced to generic defaults + the stem alias matcher.
- [x] Branded as **Keel**; README/ROADMAP rewritten for a general audience.
- [x] **Arbitrary-label stems:** any number of files, labels auto-detected from
      filenames and written to an editable per-song `keel.json` (file -> label +
      per-label balance/pan/spread/master), replacing the fixed 5-type matcher.
      A label holds 1..N files, balanced as one group. Validated end-to-end
      (single + `--batch` + `--scan`) on synthetic multitracks.

## Phase 2 — Validate on real-world material (DONE)
- [x] Run on several real multitracks; confirm the default balance generalizes.
      Validated on three deliveries (Cambridge MT raw rock kit, a synth-heavy
      17-track multitrack, and a 5-stem pre-mixed set) at 44.1 and 48 kHz. Two
      real bugs surfaced and were fixed: a mixed mono/stereo group crash, and
      per-component drum mics scattering to `other` instead of grouping as one
      kit. Auto-detect rewritten to token/word-boundary matching + a scan-time
      mapping review so mislabels are visible before render.
- [x] Confirm masters are loud enough and clean: all three landed exactly
      -14.0 LUFS, true-peak 3-4 dB under the -1.0 ceiling, no clipping, no NaN,
      including hot already-loud input stems (big negative balance gains).
- [x] Tune `DEFAULT_BALANCE` and the default target if real material demands it.
      Closed: no tuning needed. The defaults and the -14 LUFS target generalized
      across all three real deliveries without adjustment, so they are left
      unchanged by decision (changing them would need fresh research per the
      research-before-tweak rule).
- [x] Optional gentle **bus glue** (wired: keel.json `glue` + `--glue` + the GUI
      toggle, OFF by default). By-ear A/B rendered for song3 (glue off vs on);
      both masters land at exactly -14.0 LUFS / -4.08 dBTP and the user judged
      them ~identical, confirming glue is inaudible on already-mixed-ready stems.
      Decision: stays OFF by default (ADR-0015), kept only as an opt-in escape
      hatch. Closed.
- [x] Dither on export. Closed/not-needed: Keel is 24-bit in and out throughout,
      where dither is unnecessary. Documented future hook: add TPDF dither only
      if a sub-24-bit export path is ever introduced.
      (Dropped: a formal Matchering reference-vs-internal A/B. The optional
      reference-master path stays an opt-in GUI/CLI feature, ADR-0009; the
      internal chain is the default and recommended master, so there is no
      requirement to benchmark a reference the user does not want to match.)

## Phase 3 — Presets + richer config
- [x] Per-project overrides (file -> label, balance/pan/spread/master) via
      `keel.json` — no Python editing to mix a new song.
- [x] Named presets / "house sound" loudness profiles, selected at render with
      `build.py --preset NAME` (overrides the mapping's master block; an explicit
      `--lufs/--tp` still wins). Master-target-only by design — a preset picks how
      loud the master lands, not the instrument balance. Shipped: `streaming`
      (-14 LUFS, the default), `loud` (-10), `broadcast` (-16), all at -1.0 dBTP.
      Targets grounded in platform norms (Spotify/YouTube/Tidal -14; club -10;
      Apple Music / AES TD1008 -16). `--list-presets` prints the table.
- [x] Friendlier mapping review: a dry-run summary of the detected labels and any
      files that landed in `other`, so nothing is silently mislabelled. `--scan`
      now prints per-label file counts and an explicit `[check]` callout for
      unmatched files.

## Phase 4 — Standalone GUI
- [~] Drag-a-folder window: detect stems, show what was matched/missing.
      Scaffold built in `gui.py` (PySide6): drop/open a folder, auto-detect
      labels into an editable file->label table.
- [x] Live balance faders (relative LU) + LUFS / true-peak meters reading the
      same `meters.py` math the engine uses. Faders, post-render LUFS/TP meters,
      and real-time playback metering — "Play master" streams the rendered master
      via QtMultimedia QAudioSink and drives the meters live over a trailing 3 s
      window (display-only; the render path stays deterministic) — all in place.
- [x] One-click render to mix + master; reference-match picker; preset save/load.
      Render button (mix+master in a worker thread), reference picker, and
      save/load of both user presets and the project `keel.json`. A default-off
      "Live preview" re-renders mix + master (debounced) on each fader move.
- [~] Package as a desktop app (Windows first, then macOS). `Keel.spec`
      (PyInstaller) builds a Windows onefile `Keel.exe` and a macOS `Keel.app`;
      a GitHub Actions matrix (`.github/workflows/build-app.yml`) builds both on
      each version tag / manual run and uploads `Keel.exe` + `Keel.dmg` as
      artifacts, each gated by the frozen app's `--selftest`. macOS target is
      Apple Silicon (arm64 — the only macOS arch with a cp314 pedalboard wheel);
      Intel would need a separate 3.13 job. A Windows installer
      (`installer/keel.iss`, Inno Setup) wraps the onefile `Keel.exe` —
      Program Files / per-user install, Start Menu + optional desktop shortcut,
      and an uninstaller — built in CI and uploaded as `Keel-windows-installer`.
      STILL TODO: code-signing / notarization (Win Authenticode + Apple
      notarization) for an unsigned-warning-free install — the installer is UX
      only and does not by itself remove the SmartScreen "unknown publisher"
      prompt; that needs signing. A macOS installer (.pkg) is a follow-on.
- GUI toolkit decision: **PySide6 (Qt)**. Kivy was ruled out — no cp314 wheels,
  fails to install on the project's Python 3.14. PySide6 ships a stable-ABI
  (abi3) wheel that runs on 3.14, looks native, and is **LGPL** — it links into
  a closed, commercially-licensed build (PyQt's GPL would not), so it fits the
  dual-license model below. GUI deps install online (`setup.ps1 -Gui`), not
  vendored — ~150 MB of Qt binaries would bloat the repo; the core engine stays
  offline-vendored.
- [x] Keep the engine importable as a library so GUI and CLI share one core:
      `keel.py` is the public API facade (re-exports mix/master/recipes/meters);
      `import keel` is the single entry point every front-end drives. No DSP fork.

## Phase 5 — VST / plugin
Architecture decided (ADR-0026): a **thin JUCE/C++ shell that shells out to the
existing Python Keel engine** — the plugin is a third front-end on the one shared
core (alongside CLI + GUI), NOT a DSP fork. The `.vst3` the DAW loads is C++
(UI + real-time pass-through + live meters); on **Apply** it bounces to a temp
WAV, runs the bundled frozen Keel engine as a child process, and reads the
mastered audio back — byte-identical to `build.py` / `gui.py` (-14 LUFS, -1 dBTP,
deterministic). No system Python needed (the frozen engine is bundled).
In-DAW model: **hybrid** — real-time live meters + an **offline "Apply" master**
(exact integrated LUFS is whole-program, so the master is inherently offline, like
HoRNet ZeroLoud / Youlean). Toolchain confirmed on the dev machine: MSVC 14.50 +
cmake 4.2.3 + VS Community 2026.
- [ ] **Master-bus plugin first** (clearest fit); stem balancer as a follow-on.
- [~] Reuse `mastering.py` DSP: via **shell-out to the frozen engine** (offline
      Apply), not a C++ re-port. A C++ DSP port is explicitly deferred and would
      only be revisited for a zero-Python-runtime build, validated against the
      Python reference (ADR-0026).
- [ ] JUCE/C++ shell: DAW integration, UI, real-time pass-through, live LUFS/TP
      meters (C++ BS.1770 / true-peak, e.g. libebur128 — display-only), audio
      capture, and the subprocess orchestration for Apply.
- [ ] **Spike (next session):** a JUCE VST3 that builds on this machine, loads in
      a DAW, passes audio, and drives live meters, with Apply wired to shell out
      to the Python engine. (This session: ADR + plan only.)
- [ ] **ARA2** as the production polish — whole-clip access so Apply needs no
      manual bounce/export (how Melodyne / SpectraLayers integrate). v1 can ship
      bounce-then-Apply; ARA removes the manual step. Review ARA + VST3 SDK
      license terms before public distribution.
- [ ] Plugin packaging (bundle the frozen engine; CI builds engine then plugin),
      presets, and parameter automation. Code-signing / notarization shared with
      the open Phase 4 packaging item.
- Licensing (ADR-0026): JUCE under AGPLv3 for the open plugin (engine is already
      AGPL); JUCE Starter (free under 20k/yr incl. donations) covers commercial
      seats until revenue crosses the threshold, then Indie (USD 800 perpetual).
      Same hybrid product model as the GUI (ADR-0025). VENOM (GPLv3) and an
      embedded Python interpreter were both rejected (ADR-0026).

## Phase 6 — Distribution
- [ ] Naming/trademark check before public launch (Keel cleared initial searches;
      verify in target markets).
- [ ] Landing page + demo audio (before/after, A/B vs. a reference), hosted as a
      **static site on GitHub Pages** (free, no server to run).
- [x] Licensing / funding model. The engine stays **AGPL-3.0** (free, open). The
      packaged **GUI app is free** for non-commercial use and for individual
      musicians making (and selling) their own music — PolyForm Noncommercial
      plus an additional grant (`LICENSE-GUI.md`); funded by **donations**
      (PayPal, GitHub Sponsor button via `.github/FUNDING.yml`). A **commercial
      license** (`COMMERCIAL-LICENSE.md`), **USD 20 one-time per seat**, is
      required only for business / redistribution use (paid product/service,
      studio/agency client work, redistribution, or closed-source engine use).
      This is lawful because the GUI stack is LGPL-safe (PySide6, ADR-0019) and
      the author holds copyright on all original code. Same model later for the
      VST/plugin. See ADR-0025 (supersedes the earlier paid-GUI plan, ADR-0024).
- [ ] Stand up the donation/commercial-purchase links on the landing page (a
      PayPal donate button; a commercial-license checkout, e.g. Gumroad / Lemon
      Squeezy / Stripe Payment Link).

## Explicit non-goals (keep scope tight)
- No ML/neural mixing — Keel is deterministic and explainable by design.
- No per-instrument tone shaping in the mix stage — stems are already treated.
- No stem separation — Keel receives finished stems, it does not make them.
- No DAW project writing — outputs are plain WAVs (until the plugin phase).
