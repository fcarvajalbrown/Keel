# Keel — automix + automaster engine.
# Copyright (C) 2026 Felipe Carvajal Brown
#
# Licensed under the GNU Affero General Public License v3.0 (see LICENSE).
# A commercial license is available — see COMMERCIAL-LICENSE.md
# or contact fcarvajalbrown@gmail.com.
"""
mastering.py  —  THE MASTER ENGINE (the "cook" for mastering).

Turns one stereo mix WAV into a finished master. Two paths, chosen automatically:

  A) REFERENCE path (preferred when a reference exists): Matchering matches the
     mix to a commercially-mastered reference track (RMS, frequency response,
     peak, stereo width). The reference dictates loudness, so target_lufs is
     ignored on this path. Pick a same-genre, same-tempo reference per song.

  B) INTERNAL path (fallback, no reference): tone/glue -> pre-normalize toward
     target -> OVERSAMPLED soft-clip (rounds the sharpest transients) ->
     OVERSAMPLED true-peak limiter (catches intersample peaks) -> trim to the
     exact target LUFS -> true-peak safety. The soft-clip + oversampled limiter
     pairing is the loud-but-clean metal-master chain (research-cited): the
     clipper takes the very top so the limiter stays clean, and limiting at 4x
     means intersample peaks are real samples the limiter can actually catch.

Deterministic. Operates on the finished stereo mix only — it cannot re-balance
instruments (that's the mixer's job; stereo mastering "can't fix the mix").
"""
from pathlib import Path
import numpy as np
import soundfile as sf

import meters

try:
    from pedalboard import (
        Pedalboard, HighpassFilter, LowShelfFilter, HighShelfFilter,
        Compressor, Limiter,
    )
except ImportError as e:  # pragma: no cover
    raise ImportError(
        "pedalboard is required. Run:  pip install -r requirements.txt"
    ) from e

try:
    from scipy.signal import resample_poly  # polyphase-FIR up/downsampling
    _HAVE_SCIPY = True
except Exception:  # pragma: no cover
    _HAVE_SCIPY = False

OVERSAMPLE = 4  # 4x is the BS.1770-4 true-peak factor; enough to catch ISPs


def _up(sig, factor):
    return resample_poly(sig, factor, 1, axis=0, window=("kaiser", 12.0))


def _down(sig, factor):
    return resample_poly(sig, 1, factor, axis=0, window=("kaiser", 12.0))


def _soft_clip(sig, ceiling_db, factor=OVERSAMPLE):
    """Oversampled tanh soft-clip at ceiling_db. The rounded curve adds far less
    audible distortion than a hard clip; oversampling stops the harmonics it does
    add from aliasing into fizz on cymbals/guitars. Knocks the sharpest transients
    down so the limiter downstream has less to do (louder, cleaner result)."""
    ceil = meters.db_to_gain(ceiling_db)
    up = _up(sig, factor) if (factor > 1 and _HAVE_SCIPY) else sig
    up = ceil * np.tanh(up / ceil)
    out = _down(up, factor) if (factor > 1 and _HAVE_SCIPY) else up
    return np.asarray(out, dtype=np.float32)


def _os_limit(sig, rate, ceiling_db, factor=OVERSAMPLE):
    """True-peak limit: run the (proven) pedalboard Limiter on the 4x-oversampled
    signal so intersample peaks are real samples it can catch, then downsample.
    Without scipy this degrades to a plain (sample-peak) limiter at base rate."""
    if factor > 1 and _HAVE_SCIPY:
        up = np.asarray(_up(sig, factor), dtype=np.float32)
        up = Pedalboard([Limiter(threshold_db=float(ceiling_db),
                                 release_ms=120.0)])(up, rate * factor)
        out = _down(up, factor)
    else:
        out = Pedalboard([Limiter(threshold_db=float(ceiling_db),
                                  release_ms=120.0)])(np.asarray(sig, np.float32), rate)
    return np.asarray(out, dtype=np.float32)


def _internal_master(mix_path, out_path, target_lufs, tp_ceiling_db):
    audio, rate = sf.read(str(mix_path), dtype="float32", always_2d=True)
    # guard --master-only on a foreign/corrupt mix: NaN/Inf samples become
    # silence so they can't poison the loudness/true-peak math (Keel's own mix
    # is always clean PCM, but the input here may be anyone's file).
    if not np.all(np.isfinite(audio)):
        audio = np.nan_to_num(audio, nan=0.0, posinf=0.0, neginf=0.0)

    # tone/glue stage only (no limiting yet): clean sub rumble, gentle tilt, glue
    tone = Pedalboard([
        HighpassFilter(cutoff_frequency_hz=28.0),
        LowShelfFilter(cutoff_frequency_hz=110.0, gain_db=1.0, q=0.7),
        HighShelfFilter(cutoff_frequency_hz=9000.0, gain_db=1.5, q=0.7),
        Compressor(threshold_db=-14.0, ratio=1.6, attack_ms=30.0, release_ms=250.0),
    ])
    audio = tone(audio, rate)

    # 1) pre-normalize toward the target so the clip+limit stages do the right
    #    amount of work (almost nothing at -14; real work at -9/-10 later).
    loud = meters.integrated_lufs(audio, rate)
    if np.isfinite(loud):
        audio = meters.apply_gain_db(audio, target_lufs - loud)

    # 2) oversampled soft-clip: round off the sharpest transients. Clip a hair
    #    ABOVE the limiter ceiling so the clipper takes the very top and the
    #    limiter cleans the rest (clipper-then-limiter spreads the loudness work).
    clip_ceiling_db = min(0.0, tp_ceiling_db + 1.0)
    audio = _soft_clip(audio, clip_ceiling_db)

    # 3) oversampled true-peak limiter to the ceiling.
    audio = _os_limit(audio, rate, tp_ceiling_db)

    # 4) trim to the EXACT target LUFS. For streaming targets this is a turn-DOWN
    #    vs. the limited signal -> exact loudness, peaks only drop, no clipping.
    loud = meters.integrated_lufs(audio, rate)
    if np.isfinite(loud):
        audio = meters.apply_gain_db(audio, target_lufs - loud)

    # 5) true-peak safety: only if a hot target pushed peaks back over the ceiling
    #    (rare at -14), re-limit then hard-trim any residual intersample peak.
    tp = meters.true_peak_db(audio, rate)
    if np.isfinite(tp) and tp > tp_ceiling_db:
        audio = _os_limit(audio, rate, tp_ceiling_db)
        tp = meters.true_peak_db(audio, rate)
        if np.isfinite(tp) and tp > tp_ceiling_db:
            audio = meters.apply_gain_db(audio, tp_ceiling_db - tp)

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(out_path), audio, rate, subtype="PCM_24")
    return {"path": "internal", "lufs": round(meters.integrated_lufs(audio, rate), 2),
            "true_peak_db": round(meters.true_peak_db(audio, rate), 2),
            "out": str(out_path)}


def _reference_master(mix_path, ref_path, out_path):
    import matchering as mg
    mg.log(warning_handler=lambda *_: None)  # quiet; engine reports its own summary
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    mg.process(
        target=str(mix_path),
        reference=str(ref_path),
        results=[mg.pcm24(str(out_path))],
    )
    audio, rate = sf.read(str(out_path), dtype="float32", always_2d=True)
    return {"path": "matchering", "reference": str(ref_path),
            "lufs": round(meters.integrated_lufs(audio, rate), 2),
            "true_peak_db": round(meters.true_peak_db(audio, rate), 2),
            "out": str(out_path)}


def master(mix_path, recipe, out_path, references_dir=None):
    """Master one mix WAV. Uses Matchering if recipe['reference'] resolves to a
    file under references_dir, else the internal chain. Returns a report dict."""
    ref = recipe.get("reference")
    if ref and references_dir:
        ref_path = Path(references_dir) / ref
        if ref_path.exists():
            return _reference_master(mix_path, ref_path, out_path)
    return _internal_master(
        mix_path, out_path,
        target_lufs=recipe.get("target_lufs", -9.0),
        tp_ceiling_db=recipe.get("tp_ceiling_db", -1.0),
    )
