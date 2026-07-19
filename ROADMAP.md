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

## Where we are: `v0.7.0-beta`

The DSP core is **done and validated**; the CLI, the desktop GUI, and the VST3
plugin all drive the same engine and all build green. There are no unfinished
code stubs left — the remaining distance to a stable **1.0** is about
**reach and launch**, not unwritten features:

- **Trust — DONE (`v0.4`).** The test suite runs in CI as a release gate on
  Windows + macOS; the VST3 plugin is built + pluginval-smoke-tested in CI; bad
  input (malformed `keel.json`, corrupt/NaN/silent audio, `--batch`) degrades
  gracefully and is covered by tests. One tag now ships GUI + plugin together.
- **Parity — DONE (`v0.5`).** The plugin's Bus-glue toggle is wired (ADR-0030),
  the dead Reference toggle is now a passive loudness/peak readout (ADR-0035), and
  the macOS plugin build (VST3 + AU) ships in CI, verified green on a Mac runner.
- **Delivery & metering depth — DONE (`v0.6`).** Every master carries a PASS/FAIL
  compliance stamp + PLR/PSR + phase-correlation meters; sub-32-bit export dithers
  (seeded TPDF); WAV/FLAC/MP3/OGG/AAC delivery formats with a post-codec true-peak
  re-measure gate; multi-target one-pass export; an opt-in loudness-keyed TP
  ceiling; album loudness-consistency mode; and deterministic reference-loudness
  matching. Suite **39 → 73**.
- **Plugin depth — DONE (`v0.7`).** The plugin now shows real BS.1770 integrated +
  short-term LUFS (the headline fix — Makeup is aimed at integrated, the number
  streaming normalizes on), LRA, loudness + gain-reduction history graphs, a
  true-peak peak-hold, and a loudness-matched A/B; plus hiDPI resize, undo/redo,
  user presets, tooltips + first-run note, host-automation plumbing, accessibility
  labels, and a plugin-only oversampling selector. The GUI mirrors LRA + the
  loudness-matched A/B. Meter/UI/packaging only — no DSP SYNC (ADR-0036).
- **DSP feature-complete** — the two sanctioned master-tone widenings
  (deterministic stereo-width, one broadband tilt knob) are still unbuilt (`v0.8`)
  and then locked/parity-proven (`v0.9`) before the freeze.
- **Launch** — no landing page, no live donation / commercial-checkout links, no
  trademark check, `README.es` is condensed not full; and the installers + plugin
  are **unsigned** (SmartScreen / Gatekeeper warnings). All of this lands together
  at `v1.0` (signing needs the publication fee paid).

The road from here to 1.0 was restructured (2026-07-18, ADR-0036): the remaining
betas are **`v0.7` plugin depth → `v0.8` DSP carve-outs → `v0.9` DSP settle**, then
the **`v1.0.0`** launch + freeze + stamp (go-to-market folds into 1.0). Staged as
betas (`v0.4` → `v0.5` → `v0.6` → `v0.7` → `v0.8` → `v0.9`), then the stamp. The
GUI and the plugin are **versioned in lockstep** — one version number, bumped
together (see CLAUDE.md "Versioning").

---

## Shipped so far (through `v0.4.0-beta`)

Condensed history; the *why* for each lives in [`docs/adr/`](docs/adr/).

### Engine core + song-agnostic CLI (DONE)
- [x] Modules: `recipes.py` (data) · `mixer.py` / `mastering.py` / `meters.py`
      (engine) · `build.py` (CLI) · `keel.py` (public library facade). Offline
      vendored wheels in `vendor/`.
- [x] Loudness-balancing mixer (per-stem LUFS → relative balance → pan → sum),
      tone processing OFF by default (stems are pre-treated). Group handling for
      multi-file delivery (N files per label balanced as one group; printed image
      preserved; optional `spread`).
- [x] Master chain: tone → pre-normalize → **oversampled soft-clip** → **4x
      true-peak limiter** → exact-LUFS normalize → TP safety; optional Matchering
      reference path. Real BS.1770-4 LUFS + 4x polyphase-FIR true-peak meters.
- [x] Song-agnostic: no hardcoded song list or folder assumptions. Arbitrary
      labels, auto-detected (token/word-boundary matching) into an editable
      per-song `keel.json`. `--stems` / `--batch` / `--scan` / `--map` modes.
      `out/REPORT.md` QC sheet on every run.

### Validated on real material (DONE — Phase 2)
- [x] Ran on three real deliveries (Cambridge MT raw rock kit, a 17-track
      synth-heavy multitrack, a 5-stem pre-mixed set) at 44.1 + 48 kHz; all
      auto-labeled correctly and mastered to exactly -14.0 LUFS, 3–4 dB under the
      -1.0 dBTP ceiling, clean. Two real bugs fixed (mono/stereo group crash;
      drum-mic scatter). Balance + target left unchanged (generalized as-is);
      dither not needed (24-bit throughout); bus glue stays OFF by default.

### Presets + config (DONE — Phase 3)
- [x] Per-project `keel.json` overrides; named loudness presets
      (`streaming` -14 / `loud` -10 / `broadcast` -16, all -1 dBTP) via
      `--preset`; `--list-presets`; `--scan` mapping review with `[check]`
      callouts for `other`.

### Standalone GUI (DONE — Phase 4 except signing)
- [x] PySide6 app: drop-a-folder → editable file→instrument dropdown (known set +
      custom) → per-label balance faders → preset save/load → reference picker →
      bus-glue toggle → one-click
      mix+master in a worker thread → post-render + live-playback LUFS/TP meters
      → save/load project. Optional debounced "Live preview" re-render on fader
      move. `keel.py` is the shared library all front-ends drive (no DSP fork).
- [x] Packaged: `Keel.spec` (PyInstaller) → Windows onefile `Keel.exe` + macOS
      arm64 `Keel.app`/`.dmg`; Inno Setup installer (`installer/keel.iss`);
      `.github/workflows/build-app.yml` builds both on a `v*` tag and publishes a
      prerelease. **Unsigned** (see v1.0.0 below).

### VST3 plugin (DONE — Phase 5 first cut)
- [x] Self-contained real-time master (ADR-0029): a faithful C++ port of
      `mastering.py`'s chain (tone → static Makeup → oversampled soft-clip → 4x
      true-peak limiter), live LUFS/TP meters, delivery by DAW export. No offline
      Finalize, no bundled engine. Master-bus only (a stereo master can't
      re-balance — ADR-0001).
- [x] JUCE 8.0.9 / CMake / MSVC; auto-installs to the per-user VST3 folder;
      `KeelLookAndFeel` matches the standalone's visual language. Shipped in
      `v0.3.0-alpha` as `Keel-VST3-windows-0.3.0.zip` (built locally, attached by
      hand — **not in CI yet**).

### Licensing / funding (DONE — Phase 6 partial)
- [x] Hybrid model (ADR-0025): engine **AGPL-3.0**; GUI **free** for
      non-commercial + individual musicians (PolyForm + grant,
      `LICENSE-NONCOMMERCIAL.md`); **USD 20 one-time per seat**
      (`COMMERCIAL-LICENSE.md`) only for business/redistribution; donations
      (PayPal + `.github/FUNDING.yml`). Same model for the plugin (JUCE AGPLv3 /
      Starter, ADR-0026). 29 ADRs backfilled.

---

## Road to 1.0

Staged milestones — `v0.4` → `v0.5` → `v0.6` (shipped) → `v0.7` → `v0.8` → `v0.9`
→ `v1.0.0`. Each is a real release, revertable in isolation; the betas are
publishable so changes can be tested in stages. The ordering after `v0.6` was
restructured on 2026-07-18 (ADR-0036) so all DSP work finishes by `v0.8` and
spends `v0.9` proving stable, keeping the DSP freeze clean. **Code-signing is
deliberately the very last step** — it gates only the `v1.0.0` stamp, nothing
before it.

### `v0.4.0-beta` — Harden & CI (trust every build)  ✓ shipped
Made the build trustworthy before adding reach.
- [x] Run the `tests/` unittest suite in CI as a **merge/release gate**
      (Python job on Windows + macOS).
- [x] Build the **plugin in CI** (Windows VST3) and attach the zip to the
      release automatically, instead of building locally and uploading by hand.
- [x] **Edge-case tests + graceful degradation:** the engine now sanitizes
      NaN/Inf samples to silence at load and surfaces clear, user-facing errors
      for an unreadable/corrupt audio file and a malformed (hand-edited)
      `keel.json` (kept intact, never auto-overwritten); `--batch` reports a bad
      job and carries on. Covered by new tests (silent / NaN / corrupt audio,
      samplerate mismatch, malformed + missing `keel.json`, a `--batch`
      integration run). Suite **19 → 39**.
- [x] **Expanded instrument set + GUI dropdown.** The known set now also covers
      **piano, organ/keys, backing vocals, aux percussion**, each its own balance
      group with a research-backed default level; aux perc / organ group apart
      from the kit / synth. The GUI file→label field is an **editable instrument
      dropdown** sourced from one canonical list (`recipes.KNOWN_LABELS`) so UI +
      engine can't drift — custom labels still allowed (delivery-agnostic).
- [x] Wire the GUI `--selftest` (and a plugin pluginval smoke check) into CI as
      gates.
- [x] Release pipeline: one `v*` tag produces GUI + plugin assets together.

### `v0.5.0-beta` — Plugin parity + cross-platform  ✓ shipped
Bring the plugin level with the GUI's reach.
- [x] **Wire the Bus-glue toggle** into the live C++ chain (was always-on). The
      toggle gates the master glue comp; default ON keeps the out-of-box master in
      sync with `mastering.py` (DSP SYNC RULE honoured — no Python change needed,
      default-on preserves parity), OFF is a labelled plugin-only deviation. By-ear
      A/B (below) is the remaining sign-off.
- [x] **Reference control resolved (ADR-0035).** A live reference *match* is out of
      scope for the plugin (Matchering is offline/Python and a real match is ML-ish,
      against the deterministic doctrine), so the dead `reference` toggle was
      replaced with a **passive reference readout**: load a file → it is measured
      once, offline, on a background thread → its **integrated LUFS + true-peak**
      show next to the live meters. No DSP-master change (metering/UI only, no DSP
      SYNC). The spectral match stays the offline Matchering path in the CLI/GUI.
- [x] **macOS plugin build (VST3 + AU)** in CI, attached to the release. The
      `plugin` job is now a windows/macos matrix; macOS builds VST3 + AU (Xcode
      generator), pluginval-smoke-tests both, and packages
      `Keel-plugins-macos-<ver>.zip` for the release. AU is a macOS-only JUCE
      wrapper over the same processor — no DSP change. **Verified green on a real
      `macos-latest` runner** (plugin-only `workflow_dispatch`: VST3 + AU built and
      pluginval-passed).
- [ ] **By-ear A/B** sign-off: plugin live master vs a `build.py` render of the
      same audio (expect close, not identical) — user task.
- [x] **libebur128-backed reference meter** for tighter `pyloudnorm` parity. The
      offline reference readout (ADR-0035) now measures integrated LUFS + true-peak
      with libebur128 (canonical ITU-R BS.1770) instead of a JUCE-RBJ K-weighting,
      so it tracks `meters.py`/pyloudnorm to ~0.1 LU. libebur128 (MIT) is fetched
      online like JUCE, built static, pinned `v1.2.6`; it runs on the reference
      worker thread only (integrated mode allocates per block), so the live chain
      and DSP are untouched (no DSP SYNC). Verified green on Windows + macOS CI.

> **Candidates (2026-06-22 research sweep, not committed).** The plugin's by-ear
> Makeup gain is steered by a *momentary* LUFS meter, but streaming normalizes on
> *integrated* LUFS — so users aim at the wrong number. These are mostly
> correctness/credibility fixes, all in-scope + deterministic (meter/packaging
> only, no DSP-master change):
> - **Integrated + short-term LUFS, LRA, loudness-history graph** in the plugin
>   (fixes the Makeup-by-ear target gap).
> - **Gain-reduction history + true-peak peak-hold** (makes the "barely limits at
>   -14" claim visible/auditable).
> - **Loudness-matched bypass / A-B** (proves *character*, not just level — Keel
>   deliberately raises loudness).
> - **Reference loudness/peak readout** — DONE (ADR-0035): the chosen resolution of
>   the Reference-toggle fork. Shows a loaded reference's integrated LUFS / true-peak
>   next to the master, no live ML/spectral match (that stays the offline Matchering
>   path).
> - **AU plugin format** (+ optional CLAP) — AU is mandatory for Logic/Mac,
>   near-zero DSP work; pairs with the macOS build item.
> - **hiDPI resize, undo/redo, user presets, tooltips/first-run note** (the
>   delivery-by-DAW-export workflow is non-obvious). Do NOT add OpenGL/GPU
>   rendering — it worsens JUCE VST3 hiDPI scaling; the software renderer is right.
> - Clean host **automation** plumbing + **accessibility** labels.
> - **Oversampling-quality selector on the plugin's live chain** (decided
>   2026-06-22) — the live master is already approximate, so a quality/CPU selector
>   is safe and useful here. The CLI/GUI stays fixed so byte-identical determinism
>   holds. No DSP-SYNC issue (reference math unchanged).

### `v0.6.0-beta` — Delivery & metering depth  ✓ shipped
An engine-side milestone: a cluster of in-scope, deterministic wins. These turn
Keel's "loudness/TP-safe" *marketing* into a *measured guarantee* the AI-mastering
competitors can't honestly make. None touch the master tone math, so **no DSP SYNC**
was needed (the dither seed is a new render-path carve-out, not a master-math
change). Test suite **39 → 73**.
- [x] **Dither (TPDF, optional noise-shaping)** at sub-32-bit export only, via a
      **seeded-PRNG** carve-out so "same stems + recipe + seed = identical output"
      still holds (`dither.py`; `--bit-depth {16,24,32}` / `--dither {tpdf,shaped}`).
      Defaults (24-bit, no dither) reproduce the historical output byte-for-byte.
- [x] **Post-codec true-peak re-measure + TP-verify gate:** decode each encoded
      file and re-measure true-peak, grading PASS/WARN/FAIL against the ceiling
      (AAC decoded via ffmpeg). Read-only/advisory — never reshapes the master.
- [x] **Multi-target one-pass export** (`--targets streaming,-16,loud`): one master
      per target, each re-running the chain so every file is genuinely at-spec, in
      its own non-colliding file.
- [x] **Encoded output formats** (`--format flac,mp3,ogg,aac`): FLAC/MP3/OGG via
      libsndfile (offline-clean), AAC via optional ffmpeg. FLAC stays bit-exact;
      the lossy formats are deterministic given the encoder version but NOT part of
      the byte-identical guarantee (that stays a PCM/WAV promise). Still **no DAW
      project/session files** — that remains a non-goal.
- [x] **True-peak ceiling keyed to loudness** (`--auto-tp`: -14 → -1, -9 → -2 dBTP),
      an **opt-in overridable default** (an explicit `--tp` always wins). Off by
      default, so PRESETS / DEFAULT_MASTER / the fixed -14/-1 targets are unchanged.
- [x] **PASS/FAIL compliance stamp** in `out/REPORT.md` + **PLR/PSR** and
      **phase-correlation** meters (arithmetic on values Keel already computes).
- [x] **Album loudness-consistency mode** (`--album` with `--batch`): masters each
      track to a per-track target keyed to its offset from the album's integrated
      loudness, so relative track loudness is preserved while the album lands on
      target. Plus **deterministic replayable reference loudness** (`--match-loudness`
      extracts a reference's integrated LUFS as a plain, replayable target — the
      non-ML face of reference matching; the spectral match stays offline Matchering).

### `v0.7.0-beta` — Plugin depth (metering + UX)  (ADR-0036)  ✓ shipped
Turned the plugin from "works" into "trustworthy and pro-grade". The credibility
gap: Makeup was steered by a *momentary* LUFS meter while streaming judges
*integrated* LUFS, so users aimed at the wrong number. **All meter/UI/packaging — no
master-tone math changed, so no DSP SYNC in this milestone.**
- [x] **Metering / credibility (plugin):** integrated + short-term LUFS meters
      (the headline fix), **LRA** readout, a **loudness-history graph**,
      **gain-reduction history**, **true-peak peak-hold**, and a
      **loudness-matched A/B bypass** (proves *character*, not just level — Keel
      deliberately raises loudness).
- [x] **UX / quality-of-life (plugin):** hiDPI resize, undo/redo, user presets,
      tooltips + a first-run note (delivery-by-DAW-export is non-obvious),
      host-automation plumbing, accessibility labels. **No OpenGL/GPU** (it worsens
      JUCE VST3 hiDPI scaling — see non-goals).
- [x] **Oversampling-quality selector** on the plugin's live chain (ADR-0033) —
      plugin-only; the CLI/GUI stays fixed so byte-identical determinism holds.
- [x] **GUI mirror:** brought the useful additions into `gui.py` too —
      loudness-matched A/B and richer post-render meters (LRA alongside the
      existing PLR/PSR + phase-correlation).

### `v0.8.0-beta` — DSP carve-outs (stereo-width + tilt)  (ADR-0037)
The two sanctioned master-tone widenings, promoted from post-1.0. Both **opt-in /
off-by-default** so the deterministic default master and the "printed image
preserved" promise are unchanged. Both touch the master math, so **each carries a
DSP-SYNC mirror into the plugin C++ chain (ADR-0029) and an A/B re-check.**
- [ ] **Deterministic stereo-width** — a flat linear M/S side-gain (NOT EQ),
      placed **before** the true-peak limiter so the -1 dBTP guarantee holds. Off
      by default (side-gain = 1.0). Lands in `mastering.py` / `recipes.py` + mirror.
- [ ] **Single broadband tilt knob** — one deterministic brighter/darker curve on
      the master; NOT per-band, NOT M/S (those stay non-goals). Neutral by default
      (tilt = 0). Lands in `mastering.py` / `recipes.py` + mirror.
- [ ] Note the DSP-SYNC in the commits; leave settling/parity proof to `v0.9`.

### `v0.9.0-beta` — DSP settle & freeze-prep  (ADR-0038)
No new master math. Prove the v0.8 carve-outs stable and the two implementations
in sync, so the 1.0 freeze stamps an already-settled engine. This milestone is the
"solution" that lets the carve-outs land pre-1.0 without endangering the freeze.
- [ ] **Automated Python↔C++ parity harness** — render a fixed battery of test
      signals through `mastering.py` and through a small **headless C++ render**
      built from the plugin sources; measure the deltas (integrated LUFS,
      true-peak, coarse spectral/RMS-per-band) and **assert each within tolerance**;
      wire it into CI. Tolerance-based, not a null (the C++ limiter won't null
      pedalboard's, ADR-0029). Turns the manual DSP SYNC promise into a gate.
- [ ] **Golden-file regression tests** for stereo-width + tilt at representative
      settings (incl. off/neutral), locking their output against drift.
- [ ] **True-peak stress validation** with width + tilt engaged at extreme settings
      across the real deliveries — the -1 dBTP guarantee must still hold.
- [ ] **Written frozen-DSP spec sheet** — every master stage, coefficient, and
      order — the precise reference the 1.0 freeze is declared against.
- [ ] **By-ear A/B sign-off** on the carve-outs (Python render vs plugin) — user
      task.
- [ ] **Freeze-candidate ADR** declaring the DSP ready to freeze and naming the
      residual parity tolerance as a measured quantity.

### `v1.0.0` — Launch + Stable (go-to-market + signing, the last gate)
The public debut: stand up everything a stranger needs to find, trust, and pay for
Keel, then sign, freeze, and stamp. Go-to-market moved here from the original
`v0.7` (ADR-0036). Signing is the only part that depends on paying the fee.

**Go-to-market:**
- [ ] **Landing page** on GitHub Pages (tagline, before/after demo, download
      buttons, donate + commercial-checkout links).
- [ ] Stand up **donation + commercial-license checkout** links (PayPal donate;
      a USD 20/seat checkout — Gumroad / Lemon Squeezy / Stripe Payment Link).
- [ ] **Trademark verification** for "Keel" in target markets (cleared initial
      web searches; verify formally before public launch).
- [ ] **`README.es` full parity** (does/doesn't table, full `keel.json` schema,
      presets table, project structure, library/tests/GUI-build sections).
- [ ] Before/after demo audio from the user's **own** material (publish-safe).

> **Go-to-market candidates (2026-06-22 research sweep, not committed).** Sharpen
> the items above with what indie audio devs actually find works:
> - **Before/after A-B audio player** is the single highest-leverage conversion
>   asset (and the artifact reviewers reuse) — must be honestly level-matched.
> - For checkout, prefer a **Merchant-of-Record** (Lemon Squeezy / Paddle, ~5% +
>   50c/sale) over raw Stripe: a solo dev can't track global VAT; the MoR remits
>   it. Use **simple license keys, not iLok** (iLok repels the free-tier audience
>   at a USD 20 price).
> - **KVR Audio listing + freeware-curator pitches** (Bedroom Producers Blog,
>   Plugins4Free) — free, durable discovery; Keel's free-for-individuals angle is
>   exactly what they cover.
> - **Docs + a "first master in 60s" tutorial**; targeted reviewer seeding (give a
>   few mixing/mastering YouTubers a seat + clean demo project — don't mass-post).
> - **Free-vs-paid differentiation decision:** what does the USD 20 seat add over
>   the free individual tier (watermark/length-cap on the unpaid path vs feature
>   cap)? An explicit call, not a silent one.

**Sign, freeze, stamp:**
- [ ] **Windows Authenticode** signing of the installer + `Keel.exe` (removes the
      SmartScreen "unknown publisher" warning).
- [ ] **Apple notarization** of `Keel.app` / `.dmg` and the macOS plugin (removes
      the Gatekeeper warning).
- [ ] Drop the `-alpha`/`-beta` tag; **freeze the DSP** — the two-disconnected-
      impls risk (DSP SYNC RULE) is discharged by the `v0.9` parity harness +
      frozen-DSP spec sheet (ADR-0038), so this stamps an already-settled engine.
- [ ] Final docs/links sweep so nothing points at a stale version or asset URL
      (part of every release per CLAUDE.md "Versioning (STRICT)").
- [ ] Tag **`v1.0.0`** covering the GUI + plugin **in lockstep**.

> **Signing note (2026-06-22 research).** For Windows, prefer **Azure Trusted
> Signing (~USD 10/mo, near-instant SmartScreen reputation)** over an EV cert —
> Microsoft removed EV's first-download bypass in 2024, so an EV cert costs ~20-30x
> for no advantage. Caveat: confirm a Chile-based individual can enroll (as of
> 2025 it wanted a US/CA billing identity); if not, an OV cert is the fallback.
> Apple notarization is USD 99/yr and only worth it once a Mac build ships.

---

## Post-1.0 (later polish, not blocking)
Ordered by value/likelihood (most valuable first):
> **Moved earlier (2026-07-18, ADR-0037):** deterministic **stereo-width** and the
> single broadband **tilt knob** were promoted from here into **`v0.8.0-beta`** so
> 1.0 ships feature-complete; a dedicated `v0.9` settle milestone (ADR-0038) guards
> the freeze. They are no longer post-1.0.
- **macOS `.pkg` installer + Linux frozen binary** — distribution reach; the script
  already runs on Linux, so the binary is low-effort.
- **Formal legal review of the dual-license texts** — do once commercial traction
  warrants the spend.
- **Intel-mac builds** — demand-gated; the author is on Apple Silicon and arm64 is
  the current target, so build this only if Intel-mac users actually appear.
- **AAX (Pro Tools) plugin format** — niche audience, high overhead (Avid developer
  registration + PACE signing); lowest priority unless a Pro Tools audience is
  confirmed.

## `v2.0` — Reach beyond desktop (mobile + web; large, post-1.0)
The biggest expansion by far. Intended sequence (decided 2026-06-22):
**Android -> iOS -> web**, where mobile reuses the plugin's C++ chain (approximate,
plugin-grade master) and web is the only path that keeps the exact spec.

1. **Android** (first) — no universal plugin-host standard, so a **standalone JUCE
   app** (Oboe for audio). Python doesn't run on mobile, so this runs the **C++
   master chain** (approximate, like the plugin), not the exact engine. Most build
   effort of the three; weakest host integration (no DAW plugin model).
2. **iOS** (second) — a JUCE **AUv3** extension running the same **C++ plugin
   chain** inside iOS DAWs (GarageBand / Cubasis / AUM); reuses the existing plugin
   code. Approximate, not exact.
   - **NOT** Apple Intelligence / on-device LLM. That would be **ML**, Keel's
     hardest non-goal (deterministic, no neural nets) — an LLM-driven mastering
     tool is a **separate product in its own repo**, not Keel. Keep Keel's iOS
     build a faithful port of the deterministic chain.
3. **Web** (last, **MAYBE** — least committed) — if pursued, run the **existing
   Python engine server-side** (upload stems -> mix + master, the LANDR model).
   This is the only surface that preserves the **exact guaranteed-spec master**
   because it reuses the real engine; cost is hosting + running a service +
   handling user stem uploads/privacy. (A client-side WASM port would give only the
   *approximate* C++ chain, so it was rejected for the web path.)

---

## Explicit non-goals (keep scope tight)
- No ML/neural mixing — Keel is deterministic and explainable by design.
- No per-instrument tone shaping in the mix stage — stems are already treated.
- No stem separation — Keel receives finished stems, it does not make them.
- No **DAW project / session file** writing (`.als`, `.logicx`, ...) — a huge
  per-DAW maintenance surface for niche benefit; the plugin masters in-DAW. (Richer
  *audio* export — MP3/OGG/FLAC/AAC + WAV — IS now in scope, see v0.6. Revised
  2026-06-22.)

Research-confirmed declines (2026-06-22) — competitors do these; Keel deliberately
does not, because each breaks the deterministic / balance+master-only mandate:
- No **mid/side EQ** or **multiband compression** on the master — both are
  tone-shaping; Keel's doctrine is "fix balance in the recipe and re-mix." (The one
  allowed widening is a single broadband master tilt knob, post-1.0 — NOT per-band,
  NOT M/S. Revised 2026-06-22.)
- No **genre/AI tonal matching** (Ozone Master Assistant / LANDR) or **adaptive
  "fix-it" / master-rebalance** (Gullfoss / Ozone Master Rebalance) — ML and/or
  a stereo master trying to re-balance instruments (ADR-0001 says it can't).
- No **user-variable oversampling on the deterministic CLI/GUI path** — it would
  break "same stems + recipe = identical output" (visible/fixed is fine). (A
  quality selector on the plugin's already-approximate live chain IS allowed, see
  v0.5. Revised 2026-06-22.)
- No **OpenGL/GPU UI** — it worsens JUCE VST3 hiDPI scaling for no benefit here.

Considered and declined (2026-06-22) — in-scope-shaped but not worth it:
- No **ADAA soft-clip** — cleaner aliasing at lower CPU, but rewriting the clip
  math forces a full DSP-SYNC re-validation across `mastering.py` + the C++ chain
  for a marginal payoff at -14 (the clipper barely engages there), and it fights
  the 1.0 DSP freeze.
- No **loudness "drive/intensity" macro** — redundant: the plugin already exposes
  Makeup (the by-ear drive) and the CLI/GUI has target-LUFS + presets, so a macro
  adds UI without new capability and risks implying a tonal change.
- No **linear-phase option** on the fixed tone filters — small audible benefit at
  Keel's gentle settings, but it adds pre-ringing + latency (bad for the live
  plugin) and is another master-math change under the DSP SYNC RULE.
- No **ARA2** for the plugin — ARA2 exists for plugins that need random access to
  the whole host timeline (Melodyne-style pitch/time editing, spectral repair).
  Keel is a real-time master-bus processor that delivers via live DAW export, so
  ARA2 buys it nothing for large added complexity. (Moved here from post-1.0,
  2026-06-22.)
