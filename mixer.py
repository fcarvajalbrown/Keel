# Keel — automix + automaster engine.
# Copyright (C) 2026 Felipe Carvajal Brown
#
# Licensed under the GNU Affero General Public License v3.0 (see LICENSE).
# A commercial license is available — see COMMERCIAL-LICENSE.md
# or contact fcarvajalbrown@gmail.com.
"""
mixer.py  —  THE MIX ENGINE (the "cook" for mixing).

Turns a folder of stems + a declarative mix recipe (recipes.py) into one stereo
mix WAV. Rule-based loudness-balancing: normalize each stem to an internal
anchor, apply the recipe's relative balance, pan equal-power, optionally run each
stem through a built-in pedalboard chain (HPF/EQ/comp/reverb), sum, glue-bus.

Deterministic: same stems + same recipe -> same mix, every time. No ML, no
randomness. (VST3 hosting is a documented future hook — see ROADMAP.)
"""
import re
from pathlib import Path
import numpy as np
import soundfile as sf

import meters
from recipes import STEM_ALIASES

try:
    from pedalboard import (
        Pedalboard, HighpassFilter, PeakFilter, Compressor, Reverb,
    )
except ImportError as e:  # pragma: no cover
    raise ImportError(
        "pedalboard is required. Run:  pip install -r requirements.txt"
    ) from e

INTERNAL_ANCHOR_LUFS = -20.0  # each stem normalized here before balance offsets
OTHER_LABEL = "other"         # fallback label for files that match no alias


# --------------------------------------------------------------------- labeling
def _tokenize(stem_name):
    """Split a filename stem into lowercase word tokens for label matching.

    Splits on separators, camelCase boundaries, and letter<->digit runs, then
    drops pure-digit tokens, so real-world stem names resolve to clean words:
        "Guitar 1"    -> ["guitar"]
        "BassAmp1"    -> ["bass", "amp"]
        "01_Kick"     -> ["kick"]
        "ELE GTR1 Dis-M80" -> ["ele", "gtr", "dis", "m"]
        "DrumsRoom"   -> ["drums", "room"]
    Matching an alias against these tokens (anchored at a token start) is what
    makes short aliases safe — "oh" hits an "OH" overhead mic, never "john"."""
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", stem_name).lower()
    tokens = []
    for part in re.split(r"[^a-z0-9]+", spaced):
        tokens += re.findall(r"[a-z]+|[0-9]+", part)
    return [t for t in tokens if not t.isdigit()]


def _match_label(stem_name):
    """Guess a label for one filename: the first STEM_ALIASES entry with an alias
    that prefixes any token of the name. OTHER_LABEL if none match."""
    tokens = _tokenize(stem_name)
    for label, aliases in STEM_ALIASES.items():
        # longest alias first so a more specific hint wins within a label
        for a in sorted(aliases, key=len, reverse=True):
            if any(t.startswith(a) for t in tokens):
                return label
    return OTHER_LABEL


def autodetect(folder):
    """Guess a label for EVERY audio file in `folder` from its filename, using
    STEM_ALIASES. Files that match no alias get OTHER_LABEL. Returns an ordered
    {filename: label} map for ANY number of files — the starting point a user
    edits (see build.py's keel.json). This is a guess, not a constraint: the
    label can be anything once edited, and a label may hold 1 or 10 files."""
    folder = Path(folder)
    mapping = {}
    for f in sorted(folder.glob("*.wav")) + sorted(folder.glob("*.flac")):
        mapping[f.name] = _match_label(f.stem)
    return mapping


def group_files(folder, mapping=None):
    """Resolve {label: [Path, ...]} for a stems folder. If `mapping`
    (filename -> label) is given it is authoritative — only its files are used,
    files it names that are missing are skipped, and the labels are whatever the
    user assigned. Without a mapping, labels are auto-detected. Files sharing a
    label are balanced as one group downstream. Raises if nothing usable found."""
    folder = Path(folder)
    if mapping is None:
        mapping = autodetect(folder)
    groups = {}
    for fn, label in mapping.items():
        p = folder / fn
        if p.exists():
            groups.setdefault(label, []).append(p)
    if not groups:
        raise FileNotFoundError(
            f"No usable stems in {folder}. Add .wav/.flac files (the mapping may "
            f"point at files that don't exist)."
        )
    return groups


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


def _process_group(label, paths, recipe):
    """Load all files of one label, balance them AS A GROUP, return a list of
    processed stereo buffers + the rate.

    Group balancing: the label's loudness target applies to the *sum* of its files,
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

    # group loudness: measure the summed group AS RENDERED, derive ONE balance gain.
    # Each file lands on a stereo bus (via _to_stereo) downstream, so the group is
    # summed to stereo here too. This both handles labels that mix mono and stereo
    # files (e.g. a kit with mono close mics + stereo overheads/room) and keeps
    # mono-source and stereo-source groups on one perceptual basis — BS.1770 reads
    # a dual-mono stereo ~3 dB louder than the same signal as a single channel, so
    # measuring every group as stereo is what makes their relative balance consistent.
    n = max(a.shape[0] for a in loaded)
    summed = np.zeros((n, 2), dtype=np.float64)
    for a in loaded:
        aa = _to_stereo(a)
        summed[: aa.shape[0]] += aa
    group_loud = meters.integrated_lufs(summed, rate)
    target = INTERNAL_ANCHOR_LUFS + recipe["balance"].get(label, 0.0)
    gain_db = (target - group_loud) if np.isfinite(group_loud) else 0.0

    spec = recipe["chain"].get(label, {})
    board = _build_chain(spec, rate)
    spread = float(recipe.get("spread", {}).get(label, 0.0))
    base_pan = recipe["pan"].get(label, 0.0)
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
        "label": label,
        "files": len(loaded),
        "pre_lufs": round(group_loud, 2) if np.isfinite(group_loud) else None,
        "gain_db": round(gain_db, 2),
        "post_lufs": round(target, 2) if np.isfinite(group_loud) else None,
    }
    return out, rate, info


# --------------------------------------------------------------------- public API
def mix(folder, recipe, out_path, mapping=None, headroom_db=-6.0, glue=False):
    """Render the stems in `folder` to a stereo mix WAV at out_path.

    `mapping` is an optional {filename: label} dict (from keel.json); without it,
    labels are auto-detected. Files sharing a label are balanced as one group,
    for any number of files per label. The stems are already FX-printed, so this
    only level-balances, pans (if asked) and sums — no tone shaping. `glue=False`
    keeps even the bus compressor off by default. Leaves the bus peaking near
    headroom_db so the master stage has room. Returns a small report dict."""
    groups = group_files(folder, mapping)
    buffers, rate, balance = [], None, []
    for label, paths in groups.items():
        bufs, r, info = _process_group(label, paths, recipe)
        rate = rate or r
        if r != rate:
            raise ValueError(f"{label} samplerate {r} != mix rate {rate}; "
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
        "groups": [f"{l}x{len(p)}" if len(p) > 1 else l
                   for l, p in groups.items()],
        "labels": list(groups.keys()),
        "rate": rate,
        "seconds": round(n / rate, 1),
        "peak_dbfs": round(20 * np.log10(float(np.max(np.abs(bus))) or 1e-9), 2),
        "balance": balance,
        "out": str(out_path),
    }
