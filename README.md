# `src/` — the automix / automaster engine (plain-language README)

This folder takes the **finished stems** of each Werther song and produces a
**balanced stereo mix** and a **loudness-matched master** — from code, the same
"recipe + cook" way the rest of this project works. Nobody drags faders by hand.

> **The stems already have the virtual instruments and effects printed in.** So
> this engine does NOT re-EQ, re-compress, or re-verb anything. It does the two
> things you actually asked for: **balance the levels** (so nothing buries
> anything) and **master** (bring the whole thing up to a competitive, safe
> loudness). Tone is left exactly as you printed it.

---

## The one-sentence version

> **You drop the stems in each song folder. You set a few numbers in a recipe
> (how loud each stem sits, how loud the final master should be). You press the
> button. Out come `*_mix.wav` and `*_master.wav`.**

Same recipe + same stems in → same mix/master out, every time. Deterministic, no
AI guessing, no randomness.

---

## What it does (and deliberately does NOT do)

| Stage | Does | Does NOT |
|---|---|---|
| **Mix** | Loudness-balances each stem to a target, pans (only if you ask), sums to stereo, leaves headroom for the master. | Add EQ, compression, or reverb to the stems (they're already treated). No tone changes. |
| **Master** | Brings the mix to a target loudness (LUFS), tames peaks with a brick-wall limiter at a true-peak ceiling. Optionally matches a commercial reference track. | Re-balance instruments. A stereo master can't fix the mix — that's the mix stage's job. |

---

## The files that matter

| File | Plain meaning | Who edits it |
|---|---|---|
| **`recipes.py`** | The **recipe** — per song: how loud each stem sits (the balance), optional pan, the master loudness target, and an optional reference track. | You edit this to change a mix/master. |
| **`mixer.py`** | The **mix cook** — loudness-balances + pans + sums the stems. | Rarely. |
| **`mastering.py`** | The **master cook** — loudness + limiter, or Matchering against a reference. | Rarely. |
| **`meters.py`** | The loudness/peak math (LUFS, true-peak), shared by both cooks. | Rarely. |
| **`build.py`** | The **button**. Loops every song: mix → master. | Rarely. |

---

## How to use it

**1. One-time setup** (installs the audio libraries — none of these touch the
parent music engine):
```powershell
pip install -r src/requirements.txt
```
Offline / no internet? The wheels are vendored — install from disk instead:
```powershell
cd src
python -m pip install --no-index --find-links vendor numpy scipy soundfile pyloudnorm pedalboard
```

**2. Put the stems in each song's folder.** The engine reads from `../song{N}/`
and matches files by name (case-insensitive, aliases allowed):

```
song1/
  drums.wav     (or kit / perc)
  bass.wav
  guitar.wav    (or gtr)
  synth.wav     (or pad / keys)
  vocals.wav    (or vox / "vocal guide")
```
A song with only 4 stems mixes fine — missing ones are just skipped. Render all
stems of one song at the same samplerate.

**3. Press the button** (from inside `src/`):
```powershell
python build.py                # mix + master every song that has stems
python build.py --mix-only     # just the mixes
python build.py --master-only  # remaster existing mixes
python build.py 2 5            # only song 2 and song 5
```

**4. Listen** to `src/out/NN_Title_mix.wav` and `src/out/NN_Title_master.wav`.
Not balanced right? Change the numbers in `recipes.py` and press the button again.

---

## Tuning a mix (the only thing you normally touch)

In `recipes.py`, `DEFAULT_BALANCE` is the relative loudness of each stem, in LU,
measured against the vocal (vocals = 0). More negative = quieter in the mix.

```python
DEFAULT_BALANCE = {
    "vocals": 0.0,    # the anchor
    "drums": -2.0,
    "bass":  -3.0,
    "guitar": -3.5,
    "synth": -6.0,
}
```

Vocal too quiet? Lower everything else, or raise the vocal toward 0. Want a
per-song tweak instead of changing the global? Add it under that song's `"mix"`:

```python
{"idx": 2, "title": "Charlotte", "folder": "song2",
 "mix": {"balance": {"guitar": -2.5, "vocals": 0.0}}, "master": {}},
```

## Tuning a master

Per song, under `"master"`:
- `target_lufs` — how loud (default **−14**, locked album-wide). Less negative =
  louder. The chain can go to −10/−11 cleanly if a song ever wants it.
- `tp_ceiling_db` — true-peak ceiling (default −1.0 dBTP).
- `reference` — a filename in `src/references/`. If set and the file exists, that
  song is mastered by **Matchering** to match that commercial track, and
  `target_lufs` is ignored (the reference sets the loudness). Without a reference
  it uses the internal chain: tone → soft-clip → oversampled true-peak limiter →
  normalize to the exact target. True-peak is metered with a real 4× polyphase
  FIR (BS.1770-4), not an estimate.

After every `python build.py`, a QC sheet is written to **`out/REPORT.md`**:
per-song stem balance (pre/post LUFS) and the final master LUFS/dBTP vs target —
one glance to confirm every song landed.

---

## Reference-matched mastering (optional, recommended)

Drop a same-genre, same-tempo, well-mastered track into `src/references/`
(e.g. a Rammstein / SOAD / Cattle Decapitation master), point a song's
`"reference"` at it, and that song's master will be matched to it (frequency
balance, loudness, stereo width). The output is only as good as the reference, so
pick carefully. References are gitignored — they're not committed.

---

## Tied to this project now, song-agnostic later

Right now `recipes.py` is hardwired to the 6 Werther songs and reads stems from
the sibling `../song{N}/` folders. The mix/master cooks themselves know nothing
about Werther. To reuse this on any project later, the only thing to change is the
`SONGS` list (point each `stems`/`folder` anywhere). See `ROADMAP.md`.

If you only remember one thing: **stems in → set the balance + loudness numbers →
press the button → balanced mix + master out.**
