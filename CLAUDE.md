# CLAUDE.md — automix / automaster engine (standalone, song-agnostic refactor)

## What this folder is

A **code-driven automix + automaster engine**: it takes a folder of **finished,
FX-printed stems** and produces a **balanced stereo mix** and a **loudness-safe
master**. Deterministic — same stems + same recipe → identical output, every run.
No ML, no randomness.

**This is a transition copy.** It was lifted on **2026-06-14** from the Werther
album project at
`C:\Users\Beetlejuice\Desktop\WERTHER\0_10SONGEXPERIMENT\src\`, where it was
hardwired to that album's 6 songs. **The mission for THIS folder is to refine it
into a fully song-agnostic, standalone tool** — usable on any project's stems,
with no album-specific assumptions. The engine modules are already generic; only
the data/orchestration layer is still coupled (see "The refactor" below).

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
   cannot re-balance instruments — fix balance in the mix recipe and re-mix.
4. **Deterministic only.** No ML, no randomness in the render path.
5. **Never hand-edit files in `out/`** — they are build artifacts, overwritten on
   the next run.

## Architecture (data → engine → button)

- **`recipes.py`** — the data. Per-entry balance (relative LU vs a vocal anchor),
  optional pan/spread, master target. **STILL ALBUM-COUPLED:** holds a `SONGS`
  list hardwired to the 6 Werther songs and points stems at `../song{N}/`.
- **`mixer.py`** — the mix cook: loudness-balance each stem-group → optional pan →
  sum, leaving headroom for the master. **Already song-agnostic.**
- **`mastering.py`** — the master cook: tone → pre-normalize → **oversampled
  soft-clip → oversampled true-peak limiter** → normalize to exact LUFS → TP
  safety. Optional Matchering reference path. **Already song-agnostic.**
- **`meters.py`** — LUFS (BS.1770-4 via pyloudnorm) + a real **4× polyphase-FIR
  true-peak meter** (scipy `resample_poly`). **Already song-agnostic.**
- **`build.py`** — the button. **STILL ALBUM-COUPLED:** loops `recipes.SONGS` and
  defaults stems to `../song{N}/`. Writes `out/REPORT.md` QC sheet.

## The refactor — make it song-agnostic (the job here)

The DSP is done and validated; only the data/orchestration is coupled. Plan:

1. **`build.py` CLI:** add `python build.py --stems <dir> --out <dir>
   [--lufs -14] [--tp -1] [--ref <file>]` that mixes+masters ANY folder of named
   stems using `DEFAULT_BALANCE` / `DEFAULT_MASTER` — no `SONGS` list required.
   Keep a `--name` for the output basename. The current `SONGS`-loop becomes one
   optional mode (batch), not the only mode.
2. **Decouple `recipes.py`:** keep `DEFAULT_BALANCE` / `DEFAULT_PAN` /
   `DEFAULT_SPREAD` / `DEFAULT_CHAIN` / `DEFAULT_MASTER` + the `STEM_ALIASES`
   matcher (all generic). **Delete the Werther `SONGS` list** (or move it to an
   example config). Optionally read a project's song list from a small JSON/TOML
   so the tool isn't editing Python to add a project.
3. **No `../song{N}/` defaults** in `build.py` — stems come from the CLI/config.
4. Keep `mixer.py` / `mastering.py` / `meters.py` free of any project-specific
   assumptions (they already are — don't regress this).
5. Update `README.md` / `ROADMAP.md` (copied here, still Werther-flavored) to the
   standalone story. Rename the package/folder when ready (`temp/` is a placeholder).

**Research-before-tweak still applies:** before changing the mixing/mastering
*approach* (loudness target, limiter design, reference-matching), do ~5 web
searches on the technique and cite them. Don't tune DSP from memory.

## Locked DSP decisions (carried over — keep unless deliberately changing)

- **Master target −14.0 LUFS, true-peak ceiling −1.0 dBTP** (streaming-optimal,
  clean). The chain can push louder (−10/−11) cleanly thanks to the oversampled
  soft-clip + true-peak limiter, but −14 is the default decision.
- Per-stem internal anchor **−20 LUFS**, then relative balance (LU) vs the vocal
  (vocals = 0). More negative = quieter.
- Master chain: tone (HPF 28 / low-shelf / air / glue comp) → pre-normalize toward
  target → oversampled tanh soft-clip (rounds sharpest transients) → 4×
  oversampled pedalboard limiter (true-peak) → normalize to exact LUFS → TP
  safety. Validated: at −14 it barely limits, leaving ~3–4 dB true-peak headroom.

## Setup / running

```powershell
# online
pip install -r requirements.txt
# offline (wheels are vendored for Windows / CPython 3.14, cp314-win_amd64)
python -m pip install --no-index --find-links vendor numpy scipy soundfile pyloudnorm pedalboard
```
Deps: numpy, scipy, soundfile, pyloudnorm, pedalboard (+ optional matchering for
the reference-master path). All pip-only, vendored in `vendor/` for offline use.

Today (pre-refactor) it still runs the Werther way:
```powershell
python build.py        # loops recipes.SONGS (album-coupled — to be replaced by the CLI above)
```
After the refactor it should run:
```powershell
python build.py --stems "C:\path\to\stems" --out out --lufs -14
```

## What was intentionally NOT copied

The Werther song stems, the `out/` build artifacts, `references/` audio, and
`__pycache__`. Also left behind: the removed `ab_match.py` A/B helper (the user
doesn't use it). `out/` and `references/` here are empty (just `.gitkeep`).
