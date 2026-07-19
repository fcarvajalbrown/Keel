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


def short_term_lufs_max(audio, rate, window_s=3.0, hop_s=1.0):
    """Loudest short-term loudness (LUFS): the max loudness over a sliding
    `window_s`-second window (BS.1770 short-term is a 3 s window), stepped by
    `hop_s`. Used for PSR (peak-to-short-term). Returns the whole-file integrated
    loudness when the audio is shorter than one window, and -inf on silence.

    Each window is measured with the same BS.1770-4 meter as the integrated
    value; over a 3 s window the relative gate removes nothing meaningful, so this
    tracks the true short-term envelope closely while staying fully deterministic."""
    a = _as_2d(audio)
    n = a.shape[0]
    win = int(window_s * rate)
    hop = max(1, int(hop_s * rate))
    if n < win or win <= 0:
        return integrated_lufs(a, rate)
    m = _meter(rate)
    best = float("-inf")
    for start in range(0, n - win + 1, hop):
        try:
            loud = float(m.integrated_loudness(a[start:start + win]))
        except Exception:
            continue
        if np.isfinite(loud) and loud > best:
            best = loud
    return best


def loudness_range(audio, rate, window_s=3.0, hop_s=1.0):
    """Loudness range (LRA) in LU, per EBU R128 / Tech 3342: the P95 - P10 spread of
    the gated short-term loudness distribution. Short-term loudness is measured over
    a sliding `window_s`-second window stepped by `hop_s`, absolute-gated at -70
    LKFS, then relatively gated at -20 LU below the (energy) mean; LRA is the
    difference between the 95th and 10th percentiles of what survives. Returns None
    when there isn't enough gated material (e.g. very short or silent audio).

    This mirrors the plugin's live LRA (PluginProcessor.updateLra) so the GUI/CLI
    readout and the plugin agree. Deterministic; measurement only."""
    a = _as_2d(audio)
    n = a.shape[0]
    win = int(window_s * rate)
    hop = max(1, int(hop_s * rate))
    if win <= 0 or n < win:
        return None
    m = _meter(rate)
    st = []
    for start in range(0, n - win + 1, hop):
        try:
            loud = float(m.integrated_loudness(a[start:start + win]))
        except Exception:
            continue
        if np.isfinite(loud) and loud >= -70.0:  # absolute gate
            st.append(loud)
    if len(st) < 2:
        return None
    # relative gate: -20 LU below the energy mean of the absolute-gated blocks
    energies = [10.0 ** (x / 10.0) for x in st]
    mean_loudness = 10.0 * np.log10(sum(energies) / len(energies))
    rel = mean_loudness - 20.0
    gated = sorted(x for x in st if x >= rel)
    if len(gated) < 2:
        return None

    def _pct(p):
        return gated[int(round((len(gated) - 1) * p))]

    return round(_pct(0.95) - _pct(0.10), 2)


def correlation(audio):
    """Stereo phase-correlation coefficient in [-1.0, +1.0]. +1 = fully in-phase
    (a mono signal folds down cleanly), 0 = decorrelated / wide, < 0 = out of
    phase (a mono fold-down will partially cancel — a mono-compatibility risk).
    A mono buffer is trivially +1.0. Silence -> +1.0 (nothing to cancel)."""
    a = _as_2d(audio)
    if a.shape[1] < 2:
        return 1.0
    l = a[:, 0].astype(np.float64)
    r = a[:, 1].astype(np.float64)
    denom = float(np.sqrt(np.sum(l * l) * np.sum(r * r)))
    if denom <= 0.0:
        return 1.0
    return float(np.sum(l * r) / denom)


def dynamics(true_peak, integrated, short_term_max):
    """Return (PLR, PSR) in dB from already-measured values — pure arithmetic.

    PLR (Peak-to-Loudness Ratio) = true-peak - integrated loudness: how much
    headroom the whole master leaves above its average loudness (bigger = more
    dynamic / less squashed). PSR (Peak-to-Short-term Ratio) = true-peak - the
    loudest short-term loudness: a microdynamics figure less biased by quiet
    sections. Either is None when its inputs are non-finite (e.g. silence)."""
    def _diff(a, b):
        if not (np.isfinite(a) and np.isfinite(b)):
            return None
        return round(float(a) - float(b), 2)
    return _diff(true_peak, integrated), _diff(true_peak, short_term_max)


def album_loudness(track_lufs_durations):
    """Album integrated loudness (LUFS) from per-track (integrated_lufs, seconds)
    pairs: the duration-weighted mean of the tracks' LINEAR loudness, then back to
    LUFS. This is the EBU R128 album-normalisation figure — one number for the
    whole album — used to derive the single shared gain that preserves relative
    track-to-track loudness. Silent/non-finite tracks are ignored; -inf if all
    are silent."""
    num = den = 0.0
    for lufs, dur in track_lufs_durations:
        if np.isfinite(lufs) and dur > 0:
            num += dur * (10.0 ** (lufs / 10.0))
            den += dur
    if den <= 0.0:
        return float("-inf")
    return float(10.0 * np.log10(num / den))


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
