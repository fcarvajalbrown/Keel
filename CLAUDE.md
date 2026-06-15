# CLAUDE.md — Keel (automix / automaster engine)

## What this is

**Keel** is a deterministic, code-driven **automix + automaster engine**. It
takes a folder of **finished, FX-printed stems** and produces a **balanced
stereo mix** and a **loudness-safe master**. Same stems + same recipe ->
identical output, every run. No ML, no randomness.

The DSP core is done and validated. The engine is **song-agnostic and
standalone** — it has no project-specific assumptions left in it. The mission now
is to make Keel usable by **any musician**, not just terminal users:

1. Standalone tool / CLI — **done** (this repo).
2. **Standalone GUI** — drag a folder of stems, see meters, get mix + master.
3. **VST / plugin** — run Keel's balance + master stage inside a DAW.

See `ROADMAP.md` for the phased plan and `README.md` for the user-facing story.

> History: Keel was lifted on 2026-06-14 from an album project where it was
> hardwired to that album's songs. The de-coupling refactor is complete — keep it
> that way. Do not reintroduce project-specific song lists or folder assumptions.

## Hard scope — BALANCE + MASTER only, nothing else

1. **Stems are already mixed-ready** — virtual instruments and effects (EQ, comp,
   reverb) are printed in. **Do NOT add tone processing in the mix stage.** The
   mixer only **level-balances, optionally pans, and sums**. The per-stem chain in
   `recipes.py` is intentionally empty; bus glue is off by default. The per-stem
   EQ/comp/reverb fields exist only as a corrective escape hatch — don't populate
   them unless explicitly asked.
2. **Group delivery:** multiple files of one type (e.g. 2 guitars, 2 vocals) are
   collected and balanced **as a group** (the loudness target applies to their
   sum, so doubling doesn't inflate level). Printed stereo image preserved; no
   auto-pan unless `spread` is set.
3. **Mixing balances; mastering does loudness + peak control.** A stereo master
   cannot re-balance instruments — fix balance in the recipe and re-mix.
4. **Deterministic only.** No ML, no randomness in the render path.
5. **Never hand-edit files in `out/`** — they are build artifacts, overwritten on
   the next run.

## Architecture (data -> engine -> button)

- **`recipes.py`** — the data. Generic `DEFAULT_BALANCE` / `DEFAULT_PAN` /
  `DEFAULT_SPREAD` / `DEFAULT_CHAIN` / `DEFAULT_MASTER` tables + the
  `STEM_ALIASES` matcher. `mix_recipe()` / `master_recipe()` take small override
  dicts and deep-merge them onto the defaults. **No project/song list.**
- **`mixer.py`** — the mix cook: loudness-balance each stem-group -> optional pan
  -> sum, leaving headroom for the master.
- **`mastering.py`** — the master cook: tone -> pre-normalize -> oversampled
  soft-clip -> oversampled true-peak limiter -> normalize to exact LUFS -> TP
  safety. Optional Matchering reference path.
- **`meters.py`** — LUFS (BS.1770-4 via pyloudnorm) + a real 4x polyphase-FIR
  true-peak meter (scipy `resample_poly`).
- **`build.py`** — the button (CLI). `--stems <dir>` single mode or `--batch
  <dir>` over subfolders; `--out --name --lufs --tp --ref --mix-only
  --master-only`. Writes `out/REPORT.md` QC sheet.

When the GUI/plugin lands, keep the engine importable as a shared library so all
front-ends drive one core. Don't fork the DSP.

## Locked DSP decisions (keep unless deliberately changing)

- **Master target -14.0 LUFS, true-peak ceiling -1.0 dBTP** (streaming-optimal,
  clean). The chain can push louder (-10/-11) cleanly thanks to the oversampled
  soft-clip + true-peak limiter, but -14 is the default decision.
- Per-stem internal anchor **-20 LUFS**, then relative balance (LU) vs the vocal
  (vocals = 0). More negative = quieter.
- Master chain: tone (HPF 28 / low-shelf / air / glue comp) -> pre-normalize
  toward target -> oversampled tanh soft-clip (rounds sharpest transients) -> 4x
  oversampled pedalboard limiter (true-peak) -> normalize to exact LUFS -> TP
  safety. Validated: at -14 it barely limits, leaving ~3-4 dB true-peak headroom.

**Research-before-tweak:** before changing the mixing/mastering *approach*
(loudness target, limiter design, reference-matching), do ~5 web searches on the
technique and cite them. Don't tune DSP from memory.

## Setup / running

```powershell
# online
pip install -r requirements.txt
# offline (wheels vendored for Windows / CPython 3.14, cp314-win_amd64)
python -m pip install --no-index --find-links vendor numpy scipy soundfile pyloudnorm pedalboard
```
Deps: numpy, scipy, soundfile, pyloudnorm, pedalboard (+ optional matchering for
the reference-master path). All pip-only, vendored in `vendor/` for offline use.

```powershell
python build.py --stems "C:\path\to\stems" --out out --lufs -14
python build.py --batch "C:\path\to\album" --out out
```

## Working with the user

- **Present decisions as interactive options.** When offering a choice between
  alternatives, use the arrow-selectable question UI (the blue option selector),
  not a plain-text list — for every decision, however small. The UI caps at 4
  questions per call; for longer sets, chain multiple calls. Only fall back to
  plain text if that UI is genuinely unavailable.
- **No emojis** anywhere — docs, commit messages, code, or chat. Plain text only.

## Commit conventions

- **Conventional Commits.** Format every message as `type(scope): summary`, e.g.
  `feat(cli): add --batch mode`, `fix(mastering): clamp residual true-peak`,
  `docs(readme): add badges`. Common types: `feat`, `fix`, `refactor`, `docs`,
  `chore`, `test`, `perf`, `build`. Use a scope when it adds clarity
  (`mixer`, `mastering`, `meters`, `recipes`, `cli`, `readme`, `roadmap`).
- **Logical, atomic commits.** One self-contained change per commit — don't mix a
  refactor with a feature or with doc edits. Each commit should build/compile on
  its own and be revertable in isolation. Split unrelated work into separate
  commits rather than one catch-all.

## What this repo does NOT contain

Real stems, `out/` build artifacts, `references/` audio, and `__pycache__` are not
committed. `out/` and `references/` hold only a `.gitkeep`.
