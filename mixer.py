"""
mixer.py  —  THE MIX ENGINE (the "cook" for mixing).

Turns a folder of stems + a declarative mix recipe (recipes.py) into one stereo
mix WAV. Rule-based loudness-balancing: normalize each stem to an internal
anchor, apply the recipe's relative balance, pan equal-power, optionally run each
stem through a built-in pedalboard chain (HPF/EQ/comp/reverb), sum, glue-bus.

Deterministic: same stems + same recipe -> same mix, every time. No ML, no
randomness. (VST3 hosting is a documented future hook — see ROADMAP.)
"""
from pathlib import Path
import numpy as np
import soundfile as sf

import meters
from recipes import STEMS, STEM_ALIASES

try:
    from pedalboard import (
        Pedalboard, HighpassFilter, PeakFilter, Compressor, Reverb,
    )
except ImportError as e:  # pragma: no cover
    raise ImportError(
        "pedalboard is required. Run:  pip install -r requirements.txt"
    ) from e

INTERNAL_ANCHOR_LUFS = -20.0  # each stem normalized here before balance offsets


# --------------------------------------------------------------------- stem load
def find_stems(folder):
    """Map stem-type -> [Path, ...] by matching filenames against STEM_ALIASES.

    Collects MULTIPLE files per type — double-tracked guitars (guitar_L/guitar_R,
    gtr1/gtr2) and a doubled/room vocal (vocals1/vocals2, vox_double) are standard,
    so all matches are kept and balanced as one group. Returns {stemtype: [paths]}
    for whatever is present; missing types are skipped. Raises if nothing matched."""
    folder = Path(folder)
    found = {s: [] for s in STEM_ALIASES}
    for f in sorted(folder.glob("*.wav")) + sorted(folder.glob("*.flac")):
        name = f.stem.lower()
        # longest alias first so "vocal guide" wins over "guitar"-style partials
        for stem, aliases in STEM_ALIASES.items():
            if any(a in name for a in sorted(aliases, key=len, reverse=True)):
                found[stem].append(f)
                break
    found = {s: ps for s, ps in found.items() if ps}
    if not found:
        raise FileNotFoundError(
            f"No stem WAV/FLAC found in {folder}. Expected files named like "
            f"{', '.join(STEMS)} (aliases allowed; multiples like guitar_L/R ok)."
        )
    return found


def _load(path):
    """Load audio as float32 (frames, channels) plus its samplerate."""
    audio, rate = sf.read(str(path), dtype="float32", always_2d=True)
    return audio, rate


def _to_stereo(audio):
    if audio.shape[1] == 1:
        return np.repeat(audio, 2, axis=1)
    return audio[:, :2]


# ----------------------------------------------------------------- per-stem chain
def _build_chain(spec, rate):
    """Assemble a pedalboard from one stem's recipe spec. reverb handled by caller."""
    board = []
    if spec.get("hpf"):
        board.append(HighpassFilter(cutoff_frequency_hz=float(spec["hpf"])))
    for (freq, gain_db, q) in spec.get("eq", []):
        board.append(PeakFilter(cutoff_frequency_hz=float(freq),
                                gain_db=float(gain_db), q=float(q)))
    if spec.get("comp"):
        thr, ratio = spec["comp"]
        board.append(Compressor(threshold_db=float(thr), ratio=float(ratio),
                                 attack_ms=10.0, release_ms=120.0))
    return Pedalboard(board)


def _pan(stereo, pan):
    """Equal-power pan of a stereo buffer. pan -1..+1."""
    p = (float(pan) + 1.0) * 0.25 * np.pi  # map -1..1 -> 0..pi/2
    l, r = np.cos(p), np.sin(p)
    out = stereo.copy()
    out[:, 0] *= l * np.sqrt(2)
    out[:, 1] *= r * np.sqrt(2)
    return out


def _process_group(stem, paths, recipe):
    """Load all files of one stem-type, balance them AS A GROUP, return a list of
    processed stereo buffers + the rate.

    Group balancing: the type's loudness target applies to the *sum* of its files,
    so two guitars don't end up twice as loud as one. The printed relationship
    between the doubles (their relative levels and any baked-in panning) is kept;
    we apply one shared gain to the whole group. If `spread` > 0 for this type and
    there are multiple files, they're panned symmetrically across the stereo field
    (the classic double-tracked-guitar width move); otherwise the stems' own image
    is left alone."""
    loaded, rate = [], None
    for p in paths:
        a, r = _load(p)
        rate = rate or r
        if r != rate:
            raise ValueError(f"{p} samplerate {r} != group rate {rate}; "
                             "render all stems at one rate.")
        loaded.append(a)

    # group loudness: measure the summed group, derive ONE balance gain
    n = max(a.shape[0] for a in loaded)
    summed = np.zeros((n, loaded[0].shape[1] if loaded[0].ndim > 1 else 1),
                      dtype=np.float64)
    for a in loaded:
        aa = a if a.ndim > 1 else a[:, None]
        summed[: aa.shape[0], : aa.shape[1]] += aa
    group_loud = meters.integrated_lufs(summed, rate)
    target = INTERNAL_ANCHOR_LUFS + recipe["balance"].get(stem, 0.0)
    gain_db = (target - group_loud) if np.isfinite(group_loud) else 0.0

    spec = recipe["chain"].get(stem, {})
    board = _build_chain(spec, rate)
    spread = float(recipe.get("spread", {}).get(stem, 0.0))
    base_pan = recipe["pan"].get(stem, 0.0)
    positions = (np.linspace(-spread, spread, len(loaded))
                 if spread and len(loaded) > 1 else [base_pan] * len(loaded))

    out = []
    for a, pan in zip(loaded, positions):
        a = meters.apply_gain_db(a, gain_db)
        if len(board):
            a = board(a, rate)          # empty by default (stems pre-treated)
        wet = spec.get("reverb")
        if wet:
            a = Pedalboard([Reverb(room_size=0.5, wet_level=float(wet),
                                   dry_level=1.0 - float(wet) * 0.5)])(a, rate)
        a = _to_stereo(a)
        out.append(_pan(a, pan))
    info = {
        "stem": stem,
        "files": len(loaded),
        "pre_lufs": round(group_loud, 2) if np.isfinite(group_loud) else None,
        "gain_db": round(gain_db, 2),
        "post_lufs": round(target, 2) if np.isfinite(group_loud) else None,
    }
    return out, rate, info


# --------------------------------------------------------------------- public API
def mix(folder, recipe, out_path, headroom_db=-6.0, glue=False):
    """Render stems in `folder` to a stereo mix WAV at out_path.

    The stems are already FX-printed, so this only level-balances, pans (if asked)
    and sums — no tone shaping. `glue=False` keeps even the bus compressor off by
    default; flip it on only if you want a touch of cohesion. Leaves the bus
    peaking near headroom_db so the master stage has room.
    Returns a small report dict (stems used, length, peak)."""
    stems = find_stems(folder)
    buffers, rate, balance = [], None, []
    for stem, paths in stems.items():
        bufs, r, info = _process_group(stem, paths, recipe)
        rate = rate or r
        if r != rate:
            raise ValueError(f"{stem} samplerate {r} != mix rate {rate}; "
                             "render all stems at one rate.")
        buffers.extend(bufs)
        balance.append(info)

    # sum (pad to longest)
    n = max(b.shape[0] for b in buffers)
    bus = np.zeros((n, 2), dtype=np.float32)
    for b in buffers:
        bus[: b.shape[0]] += b

    # optional gentle glue (off by default — stems are already mixed-ready),
    # then leave headroom for mastering
    if glue:
        bus = Pedalboard([Compressor(threshold_db=-12.0, ratio=2.0,
                                     attack_ms=30.0, release_ms=200.0)])(bus, rate)
    peak = float(np.max(np.abs(bus))) or 1.0
    target = meters.db_to_gain(headroom_db)
    if peak > target:
        bus *= target / peak

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(out_path), bus, rate, subtype="PCM_24")
    return {
        "stems": [f"{s}x{len(p)}" if len(p) > 1 else s for s, p in stems.items()],
        "missing": [s for s in STEMS if s not in stems],
        "rate": rate,
        "seconds": round(n / rate, 1),
        "peak_dbfs": round(20 * np.log10(float(np.max(np.abs(bus))) or 1e-9), 2),
        "balance": balance,
        "out": str(out_path),
    }
