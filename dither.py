# Keel — automix + automaster engine.
# Copyright (C) 2026 Felipe Carvajal Brown
#
# Licensed under the GNU Affero General Public License v3.0 (see LICENSE).
# A commercial license is available — see COMMERCIAL-LICENSE.md
# or contact fcarvajalbrown@gmail.com.
"""
dither.py  —  SEEDED dither + quantization for sub-32-bit export.

Dither is the one place Keel deliberately adds noise: when a float master is
reduced to a fixed-point bit depth (32-bit float -> 24- or 16-bit PCM/FLAC),
plain truncation/rounding correlates the quantization error with the signal,
producing harmonic distortion and "noise modulation" (the residual hiss pumping
with the music). Adding a tiny noise BEFORE rounding decorrelates that error:
harmonic distortion is eliminated and the noise floor becomes a steady, benign
hiss (Wise, "Dither and Noise Shaping in Digital Audio"; Audio Precision).

Keel uses TPDF (triangular PDF) dither — the sum of two independent rectangular
(uniform) sources, spanning two quantization steps (2 LSB peak-to-peak) — which
is the lowest-power dither that both removes distortion AND removes noise
modulation. It costs ~4.77 dB of added noise floor, inaudible at 24-bit and a
faint, constant hiss at 16-bit.

DETERMINISM CARVE-OUT (load-bearing): dither is random by definition, which would
break Keel's "same stems + recipe = identical output" promise. So the PRNG is
SEEDED (numpy Generator, default seed 0): the same audio + bit depth + seed +
shaping give byte-identical output, every run. This is the ONLY sanctioned
randomness in the render path, and it is fully reproducible.

Optional first-order noise shaping feeds the quantization error back into the next
sample (a 6 dB/oct high-pass on the noise) to push dither energy toward the highs
where the ear is less sensitive. It is a sequential (per-sample) loop, so it is
slower than flat TPDF and stays opt-in.

Dither ONCE, at the final export to a lower bit depth — never on the intermediate
mix. Keel therefore dithers only in the master export step, not in mixer.py.
"""
import numpy as np


def lsb(bits):
    """Size of one least-significant bit, in normalized [-1, 1) float, for signed
    `bits`-deep PCM (full scale +/-1.0 maps to +/-2**(bits-1))."""
    return 2.0 ** (-(bits - 1))


def quantize(audio, bits, seed=0, noise_shaping=False):
    """Dither and quantize float `audio` to a signed `bits`-deep grid, returned as
    float32 snapped to exact LSB multiples — write it with `subtype="PCM_<bits>"`
    (or FLAC) and the store is exact (no further rounding drift).

    TPDF dither (two summed uniform sources, 2 LSB peak-to-peak) is added before
    rounding. The PRNG is seeded (`seed`), so output is deterministic. With
    `noise_shaping=True`, a first-order error-feedback loop high-passes the noise.
    `bits >= 32` is a no-op (returns float32 unchanged) — float needs no dither."""
    a = np.asarray(audio, dtype=np.float64)
    if bits >= 32:
        return np.asarray(audio, dtype=np.float32)
    two_d = a.ndim == 2
    if not two_d:
        a = a[:, None]
    n, ch = a.shape
    step = lsb(bits)
    rng = np.random.default_rng(seed)

    if not noise_shaping:
        # flat TPDF: (u1 - u2) is triangular on (-1, 1) LSB — fully vectorized.
        tpdf = (rng.random((n, ch)) - rng.random((n, ch))) * step
        out = np.round((a + tpdf) / step) * step
    else:
        # first-order noise-shaped TPDF: sequential error feedback per channel.
        out = np.empty_like(a)
        for c in range(ch):
            xt = a[:, c] + (rng.random(n) - rng.random(n)) * step
            y = np.empty(n)
            err = 0.0
            for i in range(n):
                v = xt[i] + err
                q = np.round(v / step) * step
                err = v - q
                y[i] = q
            out[:, c] = y

    # keep values inside the signed range [-1.0, +1.0 - LSB] the PCM grid allows.
    out = np.clip(out, -1.0, 1.0 - step)
    out = out if two_d else out[:, 0]
    return out.astype(np.float32)
