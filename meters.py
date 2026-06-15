# Keel — automix + automaster engine.
# Copyright (C) 2026 Felipe Carvajal Brown
#
# Licensed under the GNU Affero General Public License v3.0 (see LICENSE).
# A commercial license is available — see COMMERCIAL-LICENSE.md
# or contact fcarvajalbrown@gmail.com.
"""
meters.py  —  loudness + peak measurement helpers (shared by mixer & mastering).

Thin wrappers over pyloudnorm (ITU-R BS.1770-4). Kept separate so both the mix
and master stages measure loudness identically. Pure measurement + gain math;
no file I/O and no effects.
"""
import numpy as np

try:
    import pyloudnorm as pyln
except ImportError as e:  # pragma: no cover - guarded for un-provisioned envs
    raise ImportError(
        "pyloudnorm is required. Run:  pip install -r requirements.txt"
    ) from e

try:
    from scipy.signal import resample_poly  # polyphase-FIR oversampling
    _HAVE_SCIPY = True
except Exception:  # pragma: no cover - linear-interp fallback if scipy is absent
    _HAVE_SCIPY = False


def _meter(rate):
    return pyln.Meter(rate)  # BS.1770-4, 400 ms blocks


def integrated_lufs(audio, rate):
    """Integrated (gated) loudness in LUFS for a (frames, channels) or mono array.

    Returns -inf for pure silence (pyloudnorm yields -inf below the gate)."""
    a = _as_2d(audio)
    try:
        return float(_meter(rate).integrated_loudness(a))
    except Exception:
        return float("-inf")


def true_peak_db(audio, rate, oversample=4):
    """True-peak (dBTP) via 4x polyphase-FIR oversampling, per ITU-R BS.1770-4.

    Upsamples each channel with a Kaiser-windowed polyphase FIR (scipy
    resample_poly) and takes the peak of the reconstructed signal — this catches
    the intersample peaks a plain sample-peak meter misses (which can sit up to
    ~+3 dB above the sample peak and clip a DAC / lossy codec). The high Kaiser
    beta gives a steep stopband so the meter neither overshoots on passband
    ripple nor undershoots on HF content. If scipy is unavailable it falls back
    to the old linear-interpolation estimate (a safety figure, not compliant)."""
    a = _as_2d(audio)
    if a.size == 0:
        return float("-inf")
    if oversample > 1:
        if _HAVE_SCIPY:
            a = resample_poly(a, oversample, 1, axis=0, window=("kaiser", 12.0))
        else:
            n = a.shape[0]
            xp = np.arange(n)
            xq = np.linspace(0, n - 1, n * oversample)
            a = np.stack([np.interp(xq, xp, a[:, c]) for c in range(a.shape[1])],
                         axis=1)
    peak = float(np.max(np.abs(a))) if a.size else 0.0
    return 20.0 * np.log10(peak) if peak > 0 else float("-inf")


def db_to_gain(db):
    return float(10.0 ** (db / 20.0))


def apply_gain_db(audio, db):
    return audio * db_to_gain(db)


def normalize_to_lufs(audio, rate, target_lufs):
    """Scale audio so its integrated loudness hits target_lufs. No-op on silence."""
    loud = integrated_lufs(audio, rate)
    if not np.isfinite(loud):
        return audio
    return apply_gain_db(audio, target_lufs - loud)


def _as_2d(audio):
    """pyloudnorm wants (frames, channels); accept mono (frames,) too."""
    a = np.asarray(audio, dtype=np.float64)
    return a[:, None] if a.ndim == 1 else a
