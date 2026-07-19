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
import dither as _dither

# Output bit depth -> libsndfile subtype. 32 is float (no dither); 24/16 are the
# dithered integer targets.
_SUBTYPE = {16: "PCM_16", 24: "PCM_24", 32: "FLOAT"}

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


def _compliance(lufs, tp, target_lufs, tp_ceiling_db, lufs_tol=0.5, tp_tol=0.1):
    """PASS/FAIL verdict for a rendered master against its spec. Keel's internal
    chain normalizes to the exact target and enforces the true-peak ceiling, so a
    PASS here is a *measured* guarantee, not marketing. On the reference
    (Matchering) path `target_lufs` is None — the reference sets loudness, so the
    loudness check is skipped and only the true-peak ceiling is asserted."""
    lufs_ok = (None if (target_lufs is None or not np.isfinite(lufs))
               else bool(abs(lufs - target_lufs) <= lufs_tol))
    tp_ok = bool(np.isfinite(tp) and tp <= tp_ceiling_db + tp_tol)
    checks = [c for c in (lufs_ok, tp_ok) if c is not None]
    return {"target_lufs": target_lufs, "tp_ceiling_db": tp_ceiling_db,
            "lufs_ok": lufs_ok, "tp_ok": tp_ok,
            "lufs_tol": lufs_tol, "tp_tol": tp_tol,
            "verdict": "PASS" if all(checks) else "FAIL"}


def _write_master(audio, rate, out_path, bit_depth, dither_mode, dither_seed):
    """Write the finished master, dithering to `bit_depth` if asked. Returns the
    audio AS WRITTEN (post-dither) so the report meters read the delivered file.
    `dither_mode`: None | 'tpdf' | 'shaped'. bit_depth 32 -> float, never dithered.
    Dither happens ONCE, here, at the final export — never on the intermediate mix."""
    if dither_mode and bit_depth < 32:
        audio = _dither.quantize(audio, bit_depth, seed=dither_seed,
                                 noise_shaping=(dither_mode == "shaped"))
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(out_path), audio, rate, subtype=_SUBTYPE.get(bit_depth, "PCM_24"))
    return audio


def _report(audio, rate, path, out_path, target_lufs, tp_ceiling_db, **extra):
    """Build a master report dict: loudness + true-peak, the PLR/PSR dynamics and
    stereo phase-correlation meters, and the PASS/FAIL compliance stamp. Shared by
    the internal and reference paths so every master carries the same QC block."""
    lufs = meters.integrated_lufs(audio, rate)
    tp = meters.true_peak_db(audio, rate)
    st = meters.short_term_lufs_max(audio, rate)
    plr, psr = meters.dynamics(tp, lufs, st)
    rep = {
        "path": path,
        "lufs": round(lufs, 2) if np.isfinite(lufs) else lufs,
        "true_peak_db": round(tp, 2) if np.isfinite(tp) else tp,
        "plr": plr, "psr": psr,
        "lra": meters.loudness_range(audio, rate),
        "correlation": round(meters.correlation(audio), 3),
        "compliance": _compliance(lufs, tp, target_lufs, tp_ceiling_db),
        "out": str(out_path),
    }
    rep.update(extra)
    return rep


def _internal_master(mix_path, out_path, target_lufs, tp_ceiling_db,
                     bit_depth=24, dither_mode=None, dither_seed=0):
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

    audio = _write_master(audio, rate, out_path, bit_depth, dither_mode, dither_seed)
    return _report(audio, rate, "internal", out_path,
                   target_lufs=target_lufs, tp_ceiling_db=tp_ceiling_db,
                   bit_depth=bit_depth, dither=dither_mode)


def _reference_master(mix_path, ref_path, out_path, tp_ceiling_db=-1.0,
                      bit_depth=24, dither_mode=None, dither_seed=0):
    import matchering as mg
    mg.log(warning_handler=lambda *_: None)  # quiet; engine reports its own summary
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    mg.process(
        target=str(mix_path),
        reference=str(ref_path),
        results=[mg.pcm24(str(out_path))],
    )
    audio, rate = sf.read(str(out_path), dtype="float32", always_2d=True)
    # Matchering writes 24-bit PCM; re-quantize/re-write only if a different bit
    # depth or dither was requested, so the default reference path is untouched.
    if dither_mode or bit_depth != 24:
        audio = _write_master(audio, rate, out_path, bit_depth,
                              dither_mode, dither_seed)
    # target_lufs is None on this path — the reference dictates loudness, so
    # compliance asserts only the true-peak ceiling (loudness check skipped).
    return _report(audio, rate, "matchering", out_path,
                   target_lufs=None, tp_ceiling_db=tp_ceiling_db,
                   reference=str(ref_path), bit_depth=bit_depth, dither=dither_mode)


def loudness_recipe_from(ref_path):
    """Extract a DETERMINISTIC, replayable master recipe from a reference track:
    measure its integrated loudness and return {'target_lufs': <LUFS>}.

    This is the deterministic, non-ML face of 'match a reference' — it captures
    the reference's LOUDNESS as a plain target Keel's internal chain reproduces
    exactly on any song, needing no reference file at replay time (unlike the
    Matchering spectral-match path, ADR-0009, which needs the file and is not
    byte-deterministic). Loudness only: the true-peak ceiling stays Keel's safe
    default, so a hot reference can't drag your master's ceiling into clip risk."""
    try:
        audio, rate = sf.read(str(ref_path), dtype="float32", always_2d=True)
    except sf.LibsndfileError as e:
        raise ValueError(f"{Path(ref_path).name} is not a readable audio file "
                         f"(corrupt or unsupported): {e}") from e
    if not np.all(np.isfinite(audio)):
        audio = np.nan_to_num(audio, nan=0.0, posinf=0.0, neginf=0.0)
    lufs = meters.integrated_lufs(audio, rate)
    if not np.isfinite(lufs):
        raise ValueError(f"{Path(ref_path).name}: can't measure loudness (silent "
                         f"or too short) — pick a finished, mastered reference.")
    return {"target_lufs": round(lufs, 2)}


def master(mix_path, recipe, out_path, references_dir=None,
           bit_depth=24, dither=None, dither_seed=0):
    """Master one mix WAV. Uses Matchering if recipe['reference'] resolves to a
    file under references_dir, else the internal chain. Returns a report dict.

    `bit_depth` (16/24/32) sets the export word length; `dither` (None|'tpdf'|
    'shaped') adds seeded TPDF dither before quantizing to a sub-32-bit depth
    (see dither.py). Defaults (24-bit, no dither) reproduce the historical output
    byte-for-byte."""
    ref = recipe.get("reference")
    if ref and references_dir:
        ref_path = Path(references_dir) / ref
        if ref_path.exists():
            return _reference_master(
                mix_path, ref_path, out_path,
                tp_ceiling_db=recipe.get("tp_ceiling_db", -1.0),
                bit_depth=bit_depth, dither_mode=dither, dither_seed=dither_seed)
    return _internal_master(
        mix_path, out_path,
        target_lufs=recipe.get("target_lufs", -9.0),
        tp_ceiling_db=recipe.get("tp_ceiling_db", -1.0),
        bit_depth=bit_depth, dither_mode=dither, dither_seed=dither_seed,
    )
