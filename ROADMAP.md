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

## Where we are: `v0.3.0-alpha`

The DSP core is **done and validated**; the CLI, the desktop GUI, and the VST3
plugin all drive the same engine and all build green. There are no unfinished
code stubs left — the remaining distance to a stable **1.0** is about
**trust, parity, reach, and launch**, not unwritten features:

- **Trust** — engine tests and the plugin build aren't in CI yet; edge cases
  (malformed `keel.json`, bad audio, `--batch`) aren't tested.
- **Parity** — the plugin's Reference / Bus-glue toggles exist in the UI but
  aren't wired to the live chain, and there's no macOS plugin build.
- **Reach** — no landing page, no live donation / commercial-checkout links, no
  trademark check, `README.es` is condensed not full.
- **Launch** — the installers and the plugin are **unsigned** (SmartScreen /
  Gatekeeper warnings); signing needs the publication fee paid.

The road from here to 1.0 is staged as **betas** (`v0.4` → `v0.5` → `v0.6`),
then the **`v1.0.0`** stamp. The GUI and the plugin are **versioned in lockstep**
— one version number, bumped together (see CLAUDE.md "Versioning (STRICT)").

---

## Shipped so far (through `v0.3.0-alpha`)

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
- [x] PySide6 app: drop-a-folder → editable file→label table → per-label balance
      faders → preset save/load → reference picker → bus-glue toggle → one-click
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

Four milestones. Each is a real release, revertable in isolation; the betas are
publishable so changes can be tested in stages. **Code-signing is deliberately
the very last step** — it gates only the `v1.0.0` stamp, nothing before it.

### `v0.4.0-beta` — Harden & CI (trust every build)
Make the build trustworthy before adding reach.
- [ ] Run the `tests/` unittest suite in CI as a **merge/release gate**
      (Python job on Windows + macOS).
- [ ] Build the **plugin in CI** (Windows VST3 first) and attach the zip to the
      release automatically, instead of building locally and uploading by hand.
- [ ] **Edge-case tests:** missing/malformed `keel.json`, corrupt / NaN / silent
      audio, samplerate-mismatch error paths, a `--batch` integration test.
- [ ] Wire the GUI `--selftest` (and a plugin smoke check) into CI as gates.
- [ ] Release pipeline: one `v*` tag produces GUI + plugin assets together.

### `v0.5.0-beta` — Plugin parity + cross-platform
Bring the plugin level with the GUI's reach.
- [ ] **Wire the Bus-glue toggle** into the live C++ chain (today glue is
      always-on); honour the DSP SYNC RULE (mirror against `mastering.py`, re-A/B).
- [ ] **Wire the Reference toggle** into the live chain — or, if a live reference
      match is out of scope for the plugin, remove the control and document why.
- [ ] **macOS plugin build (VST3 + AU)** in CI, attached to the release.
- [ ] **By-ear A/B** sign-off: plugin live master vs a `build.py` render of the
      same audio (expect close, not identical) — user task.
- [ ] Optional: libebur128-backed meter for tighter parity with `pyloudnorm`.

### `v0.6.0-beta` — Go-to-market
Stand up everything a stranger needs to find, trust, and pay for Keel.
- [ ] **Landing page** on GitHub Pages (tagline, before/after demo, download
      buttons, donate + commercial-checkout links).
- [ ] Stand up **donation + commercial-license checkout** links (PayPal donate;
      a USD 20/seat checkout — Gumroad / Lemon Squeezy / Stripe Payment Link).
- [ ] **Trademark verification** for "Keel" in target markets (cleared initial
      web searches; verify formally before public launch).
- [ ] **`README.es` full parity** (does/doesn't table, full `keel.json` schema,
      presets table, project structure, library/tests/GUI-build sections).
- [ ] Before/after demo audio from the user's **own** material (publish-safe).

### `v1.0.0` — Stable (signing is the last gate)
Sign, freeze, stamp. This is the only milestone that depends on paying the fee.
- [ ] **Windows Authenticode** signing of the installer + `Keel.exe` (removes the
      SmartScreen "unknown publisher" warning).
- [ ] **Apple notarization** of `Keel.app` / `.dmg` and the macOS plugin (removes
      the Gatekeeper warning).
- [ ] Drop the `-alpha`/`-beta` tag; **freeze the DSP** (note the two-disconnected-
      impls risk per the DSP SYNC RULE before declaring it frozen).
- [ ] Final docs/links sweep so nothing points at a stale version or asset URL
      (part of every release per CLAUDE.md "Versioning (STRICT)").
- [ ] Tag **`v1.0.0`** covering the GUI + plugin **in lockstep**.

---

## Post-1.0 (later polish, not blocking)
- ARA2 support for the plugin (seamless host integration).
- Intel-mac builds (the author is on Apple Silicon; arm64 is the current target).
- A macOS `.pkg` installer; a Linux frozen binary (the script already runs there).
- AAX (Pro Tools) plugin format.
- Formal legal review of the dual-license texts.

---

## Explicit non-goals (keep scope tight)
- No ML/neural mixing — Keel is deterministic and explainable by design.
- No per-instrument tone shaping in the mix stage — stems are already treated.
- No stem separation — Keel receives finished stems, it does not make them.
- No DAW project writing — outputs are plain WAVs (the plugin masters in-DAW).
