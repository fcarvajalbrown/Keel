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

## Phase 2 — Validate on real-world material (NEXT)
- [ ] Run on several genres' stems; confirm the default balance generalizes.
- [ ] Confirm masters are loud enough and clean (no pumping, no audible clipping,
      dBTP at/under ceiling) across material.
- [ ] Tune `DEFAULT_BALANCE` and the default target if real material demands it
      (research-before-tweak: cite sources before changing the DSP approach).
- [ ] Decide when internal master vs. a Matchering reference wins; document it.
- [ ] Optional gentle **bus glue** preset (currently off) — evaluate by ear.
- [ ] Dither on export if/when rendering below 24-bit.

## Phase 3 — Project config + presets
- [ ] Read per-project overrides (balance/pan/target/reference) from a small
      JSON/TOML so users never edit Python to mix a new song.
- [ ] Named presets / "house sound" profiles (e.g. streaming-safe vs. loud).
- [ ] Per-stem-type override surface that's safe for non-coders.

## Phase 4 — Standalone GUI
- [ ] Drag-a-folder window: detect stems, show what was matched/missing.
- [ ] Live balance faders (relative LU) + LUFS / true-peak meters reading the
      same `meters.py` math the engine uses.
- [ ] One-click render to mix + master; reference-match picker; preset save/load.
- [ ] Package as a signed desktop app (Windows first, then macOS).
- [ ] Keep the engine importable as a library so GUI and CLI share one core.

## Phase 5 — VST / plugin
- [ ] Wrap the master chain (and, where it fits, the balance stage) as a VST3 /
      AU plugin so it runs inside any DAW.
- [ ] Decide the in-DAW model: master-bus processor first (clearest fit), stem
      balancer as a follow-on.
- [ ] Reuse `mastering.py` DSP via a real-time-safe path or an offline render.
- [ ] Plugin packaging, presets, and parameter automation.

## Phase 6 — Distribution
- [ ] Naming/trademark check before public launch (Keel cleared initial searches;
      verify in target markets).
- [ ] Landing page + demo audio (before/after, A/B vs. a reference).
- [ ] Licensing/pricing model for GUI + plugin.

## Explicit non-goals (keep scope tight)
- No ML/neural mixing — Keel is deterministic and explainable by design.
- No per-instrument tone shaping in the mix stage — stems are already treated.
- No stem separation — Keel receives finished stems, it does not make them.
- No DAW project writing — outputs are plain WAVs (until the plugin phase).
