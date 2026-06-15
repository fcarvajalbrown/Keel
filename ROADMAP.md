# ROADMAP — `src/` automix / automaster engine

Single checklist for the mix/master engine. Scope is deliberately narrow:
**balanced mix + competitive, safe master** of already-FX-printed stems. Not a
full mixing console.

## Status legend
`[ ]` todo  `[~]` in progress  `[x]` done

---

## Phase 0 — Scaffold (DONE)
- [x] Folder structure: `recipes.py` (data), `mixer.py` / `mastering.py` /
      `meters.py` (engine), `build.py` (orchestrator), `out/`, `references/`.
- [x] `requirements.txt` (numpy, soundfile, pyloudnorm, pedalboard, matchering).
- [x] README / CLAUDE.md / ROADMAP.md / .gitignore.
- [x] Loudness-balancing mixer (per-stem LUFS → relative balance → pan → sum),
      tone processing OFF by default (stems are pre-treated).
- [x] Group handling for standard 2-guitar / 2-vocal delivery (balanced as a
      group; printed image preserved; optional `spread` for dry dual-tracks).
- [x] Mastering: internal LUFS+limiter chain AND optional Matchering reference path.

## Phase 1 — Make it run on the real stems (NEXT)
- [ ] `pip install -r requirements.txt` on this machine; confirm imports.
- [ ] Drop one song's real stems in `../song{N}/`; run `python build.py N`.
- [ ] Listen: is the balance right? Is the master loud enough / clean (no pumping,
      no audible clipping, dBTP at/under ceiling)?
- [ ] Tune `DEFAULT_BALANCE` and per-song `target_lufs` from what we hear.
- [ ] Decide per song: internal master vs. a Matchering reference (gather refs).

## Phase 2 — Quality / correctness
- [x] **Real true-peak meter + limiter:** `meters.true_peak_db` now does proper
      4× polyphase-FIR oversampling (scipy `resample_poly`, Kaiser β12), and the
      master chain runs an **oversampled soft-clip → oversampled true-peak
      limiter** (`mastering._soft_clip` / `_os_limit`) so intersample peaks are
      caught and loud targets stay clean. Validated on the Automix TEST stems:
      same -14.0 LUFS as the old basic-limiter master but -4.08 dBTP vs -1.09
      (≈3 dB more true-peak headroom, far less limiting). Research-cited
      (BS.1770-4, clipper-then-limiter, ISP/oversampling). Fallback to linear
      interp / base-rate limiter if scipy is ever absent.
- [x] **Loudness sanity report:** `build.py` writes `out/REPORT.md` — per-song
      stem balance (pre/post LUFS + gain) and final master LUFS/dBTP vs target.
- [ ] Optional gentle **bus glue** preset (currently `glue=False`) — evaluate by ear.
- [ ] Dither on the final 24→ (any lower bit-depth) export if we ever render 16-bit.

## Phase 3 — Reference-matched mastering polish
- [ ] Curate one reference master per song (same genre/tempo) in `references/`.
- [ ] A/B internal vs. Matchering per song; lock the winner in `recipes.py`.
- [ ] Document the chosen reference for each song.

## Phase 4 — Song-agnostic / reuse (future, per user)
- [ ] Decouple `recipes.SONGS` from the Werther layout: a `--stems <dir>
      --out <dir>` CLI so the engine masters any folder of named stems.
- [ ] Optional: read song list from a small JSON/TOML instead of `recipes.py`.
- [ ] Package as a standalone tool outside this album project.

## Explicit non-goals (keep scope tight)
- No ML/neural mixing (Tier 2/3 from the feasibility research) — out of scope.
- No per-instrument tone shaping in the mix stage — stems are already treated.
- No stem separation — we receive finished stems, we don't make them.
- No DAW automation / Mixcraft project writing — outputs are plain WAVs.
