"""Cut an audio bed for the launch GIF/Reel from a Keel-rendered master.

Matches the GIF: same length, and a gain ramp that mirrors the on-screen
loudness meter — it starts ~8 dB down (the "-22 LUFS" of the animation) and
rises to the master's full level right as the number lands on -14.0 LUFS, then
holds for the end card. Picks the most energetic window so it lands on a chorus.

    python scripts/make_launch_audio.py [INPUT_WAV] [OUT_WAV]

Defaults: input out/song3_master.wav (your own material — safe to publish),
output out/keel_instagram_audio.wav. Test masters are NOT in the repo; render
one first (build.py) or pass a path. Needs numpy + soundfile (PIL optional).
"""

import os
import sys

import numpy as np
import soundfile as sf

IN = sys.argv[1] if len(sys.argv) > 1 else "out/song3_master.wav"
OUT = sys.argv[2] if len(sys.argv) > 2 else "out/keel_instagram_audio.wav"
MP4 = "assets/keel-launch.mp4"
GIF = "assets/keel-launch.gif"

FALLBACK_LEN = 15.0    # clip length (s) if the media can't be read
START_DB = -8.0        # opening gain: mirrors the -22 LUFS start vs -14 target
RISE_A, RISE_B = 0.43, 0.76   # ramp window as a fraction of the clip (~scene C, loudness)
FADE_IN = 0.10         # anti-click fade from silence at the very start (s)
FADE_OUT = 0.30        # fade out at the end (s)
HOP = 0.5
SKIP_HEAD, SKIP_TAIL = 5.0, 3.0


def media_duration():
    # prefer the MP4 (the edit asset, exact length); fall back to the GIF
    try:
        import imageio.v2 as iio
        rd = iio.get_reader(MP4)
        d = rd.get_meta_data().get("duration")
        rd.close()
        if d:
            return float(d)
    except Exception:
        pass
    try:
        from PIL import Image, ImageSequence
        im = Image.open(GIF)
        return sum(f.info.get("duration", 0) for f in ImageSequence.Iterator(im)) / 1000.0
    except Exception:
        return FALLBACK_LEN


def smoothstep(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3 - 2 * x)


def main():
    data, sr = sf.read(IN, always_2d=True)
    n, dur = data.shape[0], data.shape[0] / sr
    clip_len = media_duration() or FALLBACK_LEN
    win = min(clip_len, max(2.0, dur * 0.6))
    win_n = int(win * sr)

    # pick the most energetic window (lands on a chorus, not the intro)
    mono = data.mean(axis=1)
    lo = int(min(SKIP_HEAD, dur * 0.1) * sr)
    hi = max(lo + 1, n - win_n - int(SKIP_TAIL * sr))
    best_start, best_rms = lo, -1.0
    for s in range(lo, hi, max(1, int(HOP * sr))):
        rms = float(np.sqrt(np.mean(mono[s:s + win_n] ** 2)))
        if rms > best_rms:
            best_rms, best_start = rms, s

    clip = data[best_start:best_start + win_n].copy()

    # gain envelope: hold at START_DB, ramp to full over [RISE_A, RISE_B], hold full
    f = np.linspace(0.0, 1.0, clip.shape[0])
    start_lin = 10 ** (START_DB / 20.0)
    ramp = smoothstep((f - RISE_A) / (RISE_B - RISE_A))
    g = np.where(f < RISE_A, start_lin,
                 np.where(f < RISE_B, start_lin + (1 - start_lin) * ramp, 1.0))
    # anti-click fades on top
    fi, fo = int(FADE_IN * sr), int(FADE_OUT * sr)
    if fi > 0:
        g[:fi] *= np.linspace(0.0, 1.0, fi)
    if fo > 0:
        g[-fo:] *= np.linspace(1.0, 0.0, fo)
    clip *= g[:, None]

    sf.write(OUT, clip, sr, subtype="PCM_24")
    print(f"audio saved: {OUT}  sr={sr}  {clip.shape[0]/sr:0.2f}s  "
          f"(ramp {START_DB:+.0f} dB -> 0 dB over {RISE_A:.2f}-{RISE_B:.2f}) "
          f"from {best_start/sr:0.1f}s of {IN} ({dur:0.1f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
