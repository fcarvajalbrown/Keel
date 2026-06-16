# Keel — Automatic Mixing + Mastering for Finished Stems (Python)

> A **deterministic** automix + automaster engine. Give it a folder of
> **finished, FX-printed stems**; it **loudness-balances** them into a stereo
> **mix** and masters that mix to a clean, **streaming-safe loudness** — built on
> **ITU-R BS.1770-4** metering and a **true-peak-limited** master chain. Same
> stems in, same master out, every run. No AI guessing, no randomness.

[![status](https://img.shields.io/badge/status-pre--release-orange.svg)](ROADMAP.md)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPLv3-blue.svg)](LICENSE)
[![commercial license](https://img.shields.io/badge/commercial%20license-available-blueviolet.svg)](COMMERCIAL-LICENSE.md)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](requirements.txt)
[![loudness](https://img.shields.io/badge/loudness-ITU--R%20BS.1770--4-brightgreen.svg)](#under-the-hood-the-dsp)
[![render](https://img.shields.io/badge/render-deterministic-success.svg)](#)

**What it does, in one line:** turn a pile of finished stems into a balanced mix
and a competitive, peak-safe master with one command — without touching your tone.

Keel is for two people. The **producer** with great stems who doesn't want to (or
can't) mix and master by hand: one command, done. The **engineer** who wants a
deterministic, scriptable balance+master stage in a pipeline: exact LUFS targets,
a real oversampled true-peak meter, reproducible to the sample, with a QC report
on every run. The long-term goal is a **standalone GUI** and a **VST/plugin** on
the same engine — see [`ROADMAP.md`](ROADMAP.md).

> Keywords: automatic mixing, automatic mastering, loudness normalization, LUFS,
> true peak, ITU-R BS.1770-4, stem balancing, limiter, mastering chain,
> deterministic audio, reproducible, Python audio, VST (planned).

---

## At a glance

| | |
|---|---|
| **Input** | Any number of finished, FX-printed stems (`.wav` / `.flac`) |
| **Output** | Balanced stereo **mix** + loudness-safe **master** (24-bit WAV) + `REPORT.md` |
| **Loudness** | Normalized to an **exact LUFS target** (default **-14**), ITU-R BS.1770-4 |
| **Peaks** | Real **4x-oversampled true-peak** limiting to a dBTP ceiling (default **-1.0**) |
| **Labeling** | **Auto-detected**, user-editable `keel.json`; **1..N files per label** |
| **Mastering** | Internal clip -> limit chain, **or** match a commercial reference (Matchering) |
| **Determinism** | Same inputs -> **identical** output. No ML, no randomness in the render path |
| **Tone** | **Untouched** — Keel balances and masters; it never re-EQs your stems |

---

## Sample run

A real 8-stem multitrack (Tally Hall, "Good Day", 3.5 min) — auto-labeled and
mastered with defaults, no manual editing:

```
$ python build.py --stems ./GoodDay --out out
mapping -> GoodDay/keel.json  (auto-detected: guitar, vocals, bass, drums, synth)
mix     -> ..._mix.wav     210.0s  -6.0 dBFS  groups: guitarx3, vocalsx2, bass, drums, synth
master  -> ..._master.wav  -14.0 LUFS  -2.76 dBTP
```

From the generated `out/REPORT.md`:

| label | files | pre LUFS | gain dB | post LUFS |
|---|---|---|---|---|
| guitar | 3 | -26.81 | +3.31 | -23.5 |
| vocals | 2 | -24.51 | +4.51 | -20.0 |
| bass   | 1 | -28.87 | +5.87 | -23.0 |
| drums  | 1 | -28.50 | +6.50 | -22.0 |
| synth  | 1 | -27.93 | +1.93 | -26.0 |

Master: **-14.0 LUFS** (exactly on target), **-2.76 dBTP** (safely under the
-1.0 ceiling). Three guitars and two vocals were each balanced as a single group.
Re-running reproduces these numbers to the sample.

---

## What Keel does (and deliberately does not)

| Stage | Does | Does NOT |
|---|---|---|
| **Mix** | Groups files by label, loudness-balances each group to a target, pans only if asked, sums to stereo, leaves headroom for the master. | Add EQ, compression, or reverb. Your stems are already treated — Keel will not touch your tone. |
| **Master** | Brings the mix to an exact LUFS target; controls peaks with an oversampled soft-clip + true-peak limiter at a dBTP ceiling; optionally matches a reference track. | Re-balance instruments. A stereo master can't fix a mix — fix the balance in the mix stage and re-run. |

---

## How it works (the signal path)

```
MIX     stems -> [group by label] -> [loudness-balance each group] -> [pan?] -> sum -> mix.wav
MASTER  mix   -> [tone/glue] -> [pre-normalize] -> [oversampled soft-clip]
              -> [4x true-peak limiter] -> [normalize to exact LUFS] -> [TP safety] -> master.wav
```

Every step is measurement-driven and deterministic. The mix leaves the bus near
-6 dBFS so the master has room; the master normalizes to your exact LUFS target
and guarantees the true-peak ceiling.

---

## Install

Recommended — a local virtual environment (keeps Keel's deps isolated, runs the
same on any machine). `setup.ps1` builds `.venv` and installs the core engine
**offline** from the vendored wheels:

```powershell
.\setup.ps1                 # create .venv + install core engine offline from vendor/
.\setup.ps1 -Online         # ...or pull from PyPI instead
.\setup.ps1 -Matchering     # also install the optional reference-master path
.\.venv\Scripts\Activate.ps1   # activate, then run build.py
```

The venv itself is never committed — it is rebuilt from `requirements.txt` /
`vendor/` on each machine.

Prefer to install straight into your current Python?

```powershell
pip install -r requirements.txt          # numpy, scipy, soundfile, pyloudnorm, pedalboard
```
Offline? The wheels are vendored:
```powershell
python -m pip install --no-index --find-links vendor numpy scipy soundfile pyloudnorm pedalboard
```
Optional: `matchering` for the reference-matched master path (vendored too, but it
pulls a heavy numba/llvmlite/pandas tree — `.\setup.ps1 -Matchering` or
`pip install matchering`).

---

## Quick start

**1. Put your stems in a folder** — any number, any names. Keel does not require a
fixed set of stems; it auto-detects a label per file, and you correct it next.

```
my_song/
  drum_kick.wav  drum_snare.wav  oh_L.wav  oh_R.wav
  bass.wav
  gtr_DI_1.wav  gtr_DI_2.wav  gtr_solo.wav
  lead_vox.wav  harmony.wav
```

**2. Run it:**
```powershell
python build.py --stems "C:\path\to\my_song" --out out
```
On the first run Keel writes **`my_song/keel.json`** (auto-detected file -> label
map + per-label balance) and renders `out/my_song_mix.wav`,
`out/my_song_master.wav`, and `out/REPORT.md`.

**3. Fix the labels, then re-run.** Auto-detect is only a guess. Open `keel.json`,
reassign any file to the right label (**a label can hold 1 or 10 files** — they're
balanced as one group), tweak the per-label balance, and run the same command
again:

```json
{
  "stems":   { "oh_L.wav": "drums", "gtr_solo.wav": "guitar", "harmony.wav": "vocals" },
  "balance": { "vocals": 0.0, "drums": -2.0, "guitar": -3.5 }
}
```

### More ways to run

```powershell
python build.py --stems ./my_song --scan                  # only (re)write keel.json, no render
python build.py --stems ./my_song --map "C:\maps\x.json"  # use a mapping file elsewhere
python build.py --stems ./my_song --preset loud           # house-sound loudness profile
python build.py --list-presets                            # list the named presets
python build.py --stems ./my_song --lufs -11 --tp -1      # push louder, set TP ceiling
python build.py --stems ./my_song --ref "C:\refs\ref.wav" # match a reference (Matchering)
python build.py --stems ./my_song --mix-only              # stop after the mix
python build.py --stems ./my_song --master-only           # remaster an existing mix
python build.py --batch "C:\path\to\album" --out out      # every subfolder (its own keel.json)
```

---

## Labeling: `keel.json`

There is no fixed stem list. Each file gets a **label**; all files sharing a label
are balanced together as one group (so two guitars hit the target together instead
of coming out twice as loud). Auto-detect seeds the map from filenames; you own it
from there. Custom labels and `other` are fine and default to 0.0 balance.

```json
{
  "stems":   { "kick.wav": "drums", "gtr_DI_1.wav": "guitar", "lead_vox.wav": "vocals" },
  "balance": { "vocals": 0.0, "drums": -2.0, "bass": -3.0, "guitar": -3.5, "synth": -6.0 },
  "pan":     {},
  "spread":  {},
  "glue":    false,
  "master":  { "target_lufs": -14.0, "tp_ceiling_db": -1.0, "reference": null }
}
```

- **balance** — relative loudness in LU vs. the vocal (vocals = 0). More negative
  = quieter. Seeded from `recipes.py` (`DEFAULT_BALANCE`).
- **pan** — `-1.0` (L) .. `+1.0` (R), equal-power. Default centered (your printed
  width is kept).
- **spread** — `0..1`; auto-pans a multi-file label symmetrically (e.g. doubled
  guitars hard L/R). Default 0.
- **glue** — `true/false`; a gentle bus-glue compressor over the summed mix.
  Default `false` (the stems are already mix-ready). CLI `--glue/--no-glue`
  overrides it. Leave off unless a sum genuinely wants light cohesion.
- **master** — `target_lufs`, `tp_ceiling_db`, and an optional `reference`
  filename. CLI `--lufs/--tp/--ref` override these.

### Presets (house-sound loudness profiles)

Instead of remembering numbers, pick a named target with `--preset`. A preset
sets only the master loudness target + true-peak ceiling (it picks how loud the
master lands, not how the instruments sit), applied at render time over the
mapping's `master` block. An explicit `--lufs/--tp` still wins over a preset.

| preset | target | ceiling | for |
|---|---|---|---|
| `streaming` (default) | -14 LUFS | -1 dBTP | Spotify / YouTube / Tidal / Amazon normalization target |
| `loud` | -10 LUFS | -1 dBTP | club / aggressive; held clean by the oversampled clip + true-peak limiter |
| `broadcast` | -16 LUFS | -1 dBTP | Apple Music / Apple Podcasts / AES TD1008 — quieter, more dynamic |

```powershell
python build.py --stems ./my_song --preset loud
python build.py --list-presets
```

---

## Under the hood (the DSP)

- **Loudness:** integrated LUFS via `pyloudnorm` (ITU-R BS.1770-4, 400 ms gated).
- **True peak:** a real **4x polyphase-FIR** oversampling meter (scipy
  `resample_poly`, Kaiser beta 12) — catches intersample peaks a sample-peak meter
  misses (up to ~+3 dB).
- **Master chain:** tone (HPF 28 / low-shelf / air / gentle glue) ->
  pre-normalize -> **oversampled tanh soft-clip** (rounds the sharpest transients)
  -> **4x-oversampled true-peak limiter** -> normalize to the exact target ->
  true-peak safety. The clip-then-limit pairing is the loud-but-clean approach:
  the clipper takes the very top so the limiter stays clean.
- **Reference master (optional):** `matchering` matches a commercial reference's
  spectrum, loudness, and stereo width; the reference then sets the loudness.
- **Defaults:** master **-14.0 LUFS / -1.0 dBTP** (streaming-optimal); per-stem
  internal anchor **-20 LUFS**. The chain pushes to -10/-11 cleanly when asked.

Every `build.py` run writes `out/REPORT.md`: per-label balance (pre/post LUFS +
gain) and the final master LUFS/dBTP vs. target — one glance to confirm it landed.

---

## Project structure

```
keel.py         # public library API: one import surface for CLI/GUI/plugin
build.py        # CLI entry point: scan -> write/read keel.json -> mix -> master -> REPORT
recipes.py      # default balance/pan/master tables + the auto-detect alias hints
mixer.py        # the mix engine: autodetect/group by label, loudness-balance, pan, sum
mastering.py    # the master engine: tone -> clip -> true-peak limit -> exact LUFS, or Matchering
meters.py       # LUFS (BS.1770-4) + 4x true-peak meter; shared gain math
<song>/keel.json# per-song mapping: file -> label, per-label balance/pan/spread, master target
out/            # rendered mixes, masters, and REPORT.md (build artifacts)
vendor/         # offline pip wheels
```

The engine is deterministic and self-contained: no network, no telemetry, no
project lock-in. Outputs are plain 24-bit WAVs.

### Use it as a library

Every front-end drives the same core through `keel.py` — the DSP is never forked
per front-end:

```python
import keel

mapping = keel.autodetect("my_song")                       # {file: label}
recipe  = keel.mix_recipe({"balance": {"synth": -4.0}})    # defaults + overrides
keel.mix("my_song", recipe, "out/song_mix.wav", mapping=mapping)
keel.master("out/song_mix.wav",
            keel.master_recipe(keel.preset_master("streaming")),
            "out/song_master.wav")
```

---

## Where Keel is headed

Today Keel is a command-line tool. The mission is to reach any musician on the
same deterministic engine:

1. **Standalone GUI** — drag a folder of stems, see the labels and loudness
   meters, get your mix + master.
2. **VST / plugin** — run Keel's balance + master stage inside your DAW.

The DSP core is done and validated. See [`ROADMAP.md`](ROADMAP.md).

---

## License

Keel is **dual-licensed**:

- **Open source: GNU AGPL-3.0** ([`LICENSE`](LICENSE)). Free to use, study,
  modify, and share — but if you distribute it or run a modified version as a
  network service, you must release your source under the AGPL too.
- **Commercial license: available** ([`COMMERCIAL-LICENSE.md`](COMMERCIAL-LICENSE.md)).
  To build on Keel inside a closed-source product or service without the AGPL's
  copyleft obligations, contact the author.

Individuals and open projects use it freely under the AGPL; companies that want it
closed-source take a commercial license.

## Author

Felipe Carvajal Brown — fcarvajalbrown@gmail.com

Copyright (C) 2026 Felipe Carvajal Brown.
