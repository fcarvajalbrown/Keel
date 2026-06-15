# Keel

![status](https://img.shields.io/badge/status-pre--release-orange)
![engine](https://img.shields.io/badge/engine-validated-brightgreen)
![python](https://img.shields.io/badge/python-3.14-blue)
![loudness](https://img.shields.io/badge/loudness-ITU--R%20BS.1770--4-blueviolet)
![render](https://img.shields.io/badge/render-deterministic-success)
![license](https://img.shields.io/badge/license-AGPL--3.0-blue)
![commercial](https://img.shields.io/badge/commercial%20license-available-blueviolet)

**Drop in your stems. Get back a balanced mix and a loudness-safe master.**

Keel is a deterministic automix + automaster engine. You give it a folder of
finished, FX-printed stems; it level-balances them into a stereo mix and masters
that mix to a clean, streaming-ready loudness. Same stems in, same master out,
every single time. No AI guessing, no randomness, no faders to ride.

> **Your stems already sound the way you want.** Keel does not re-EQ,
> re-compress, or re-verb anything. It does the two jobs that actually stand
> between a pile of stems and a finished track: **balance the levels** so nothing
> buries anything, and **master** so the whole thing hits a competitive, safe
> loudness. Your tone is left exactly as you printed it.

---

## Why Keel

You can mix and master a song by hand. It takes hours, an ear you've trained for
years, and a treated room — and the result drifts a little every time you do it.
Or you can hand a finished set of stems to an opaque AI service and hope it
guesses what you wanted.

Keel is the third option: a **transparent, repeatable, rule-based** balance +
master you can actually reason about. It is built on published loudness science
(ITU-R BS.1770-4 LUFS, true-peak metering) and a metal-grade clip-then-limit
master chain — but you drive it with a single command.

- **For the bedroom producer:** you have great stems and don't want to (or can't)
  mix and master by hand. One command turns them into a balanced, loud, safe
  track you can upload today.
- **For the working engineer:** a deterministic, scriptable balance+master stage
  for your pipeline. Exact LUFS targets, a real 4x-oversampled true-peak meter,
  reproducible to the sample, and a QC report on every run.

---

## The one-sentence version

> **Put your stems in a folder. Run one command. Out come `*_mix.wav` and
> `*_master.wav` — balanced and mastered.**

Want it different? Change a number, run it again. That's the whole loop.

---

## What it does (and deliberately does NOT do)

| Stage | Does | Does NOT |
|---|---|---|
| **Mix** | Loudness-balances each stem (and groups, like double-tracked guitars) to a target, pans only if you ask, sums to stereo, leaves headroom for the master. | Add EQ, compression, or reverb to your stems. They are already treated — Keel will not touch your tone. |
| **Master** | Brings the mix to an exact loudness target (LUFS), controls peaks with an oversampled soft-clip + true-peak limiter at a true-peak ceiling. Optionally matches a commercial reference track. | Re-balance instruments. A stereo master can't fix a mix — that's the mix stage's job. Fix the balance, re-run. |

---

## Quick start

**1. Install** (audio libraries — all free, all pip):
```powershell
pip install -r requirements.txt
```
Offline? The wheels are vendored — install from disk:
```powershell
python -m pip install --no-index --find-links vendor numpy scipy soundfile pyloudnorm pedalboard
```

**2. Put your stems in a folder.** Files are matched by name (case-insensitive,
aliases allowed):

```
my_song/
  drums.wav     (or kit / perc)
  bass.wav
  guitar.wav    (or gtr)        - two guitars? guitar_L.wav + guitar_R.wav
  synth.wav     (or pad / keys)
  vocals.wav    (or vox / "vocal guide")  - lead + double? vocals1.wav + vocals2.wav
```
A song with only some of these mixes fine — missing types are skipped. Render all
stems of one song at the same sample rate.

**3. Run it:**
```powershell
python build.py --stems "C:\path\to\my_song" --out out
```
That writes `out/my_song_mix.wav` and `out/my_song_master.wav`, plus a QC sheet
at `out/REPORT.md`.

**4. Listen.** Not balanced right? Adjust and run again (see Tuning below).

### More ways to run

```powershell
# Name the output, push louder, set the true-peak ceiling
python build.py --stems ./my_song --name single_v2 --lufs -11 --tp -1

# Master to a commercial reference instead of a fixed LUFS target
python build.py --stems ./my_song --ref "C:\refs\commercial_master.wav"

# Just the mix, or just re-master an existing mix
python build.py --stems ./my_song --mix-only
python build.py --stems ./my_song --master-only

# Batch: mix+master every subfolder of an album folder in one go
python build.py --batch "C:\path\to\album" --out out
```

---

## Tuning the mix

The balance is relative loudness, in LU, measured against the vocal (vocals = 0).
More negative = quieter in the mix. The defaults live in `recipes.py`:

```python
DEFAULT_BALANCE = {
    "vocals": 0.0,    # the anchor
    "drums": -2.0,
    "bass":  -3.0,
    "guitar": -3.5,
    "synth": -6.0,
}
```

Vocal too quiet? Pull everything else down, or raise the vocal toward 0. These
are global defaults today; per-song overrides are passed as small dicts in code
and will become a first-class CLI/GUI control (see `ROADMAP.md`).

## Tuning the master

- `--lufs` — how loud (default **-14**, streaming-optimal). Less negative =
  louder. The chain holds up cleanly down to about -10/-11.
- `--tp` — true-peak ceiling (default **-1.0 dBTP**).
- `--ref` — a reference master. If given, Keel uses **Matchering** to match that
  track's frequency balance, loudness, and stereo width, and `--lufs` is ignored
  (the reference sets the loudness). The output is only as good as the reference,
  so pick a same-genre, same-era, well-mastered track.

Without a reference, the master uses Keel's internal chain: tone (HPF / gentle
tilt / glue) -> pre-normalize -> oversampled soft-clip -> oversampled true-peak
limiter -> normalize to the exact target -> true-peak safety. True-peak is
metered with a real 4x polyphase FIR (BS.1770-4), not an estimate.

After every run, `out/REPORT.md` gives a one-glance QC sheet: per-stem balance
(pre/post LUFS) and the final master LUFS/dBTP vs. target.

---

## How it's built

| File | What it is | Who touches it |
|---|---|---|
| **`build.py`** | The button — the command-line entry point. | Run it. |
| **`recipes.py`** | The defaults — balance, pan, master target, aliases. | Edit to change the house sound. |
| **`mixer.py`** | The mix engine — loudness-balance + pan + sum. | Rarely. |
| **`mastering.py`** | The master engine — loudness + limiter, or Matchering. | Rarely. |
| **`meters.py`** | The loudness/peak math (LUFS, true-peak), shared by both. | Rarely. |

The engine is deterministic and self-contained: no network, no telemetry, no
project lock-in. Outputs are plain 24-bit WAVs.

---

## Where Keel is headed

Today Keel is a command-line tool. The mission is to make this engine available
to any musician, not just people comfortable in a terminal:

1. **Standalone GUI** — drag a folder of stems onto a window, see the balance and
   loudness meters, get your mix + master. Same deterministic engine underneath.
2. **VST / plugin** — run Keel's balance + master stage right inside your DAW.

The DSP core is done and validated. See `ROADMAP.md` for the plan.

---

## License

Keel is **dual-licensed**:

- **Open source: GNU AGPL-3.0** (see `LICENSE`). Free to use, study, modify, and
  share. The catch: if you distribute Keel or run a modified version as a network
  service, you must release your full source under the AGPL too. This keeps Keel
  and everything built on it open.
- **Commercial license: available.** If you want to build on Keel without the
  AGPL's copyleft obligations — e.g. ship it inside a closed-source product or
  service — a separate commercial license is available. See
  `COMMERCIAL-LICENSE.md`, or contact **Felipe Carvajal Brown**
  (fcarvajalbrown@gmail.com).

In short: individuals and open projects use it freely under the AGPL; companies
that want it closed-source pay for a commercial license.

Copyright (C) 2026 Felipe Carvajal Brown.

---

If you only remember one thing: **stems in -> one command -> balanced mix +
safe master out.**
