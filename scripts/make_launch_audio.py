"""Cut an audio bed for the launch video from a Keel-rendered master.

Picks the most energetic ~18 s window of the input master (so the clip lands
on a chorus, not the intro), applies short fades, and writes a clean excerpt.
Use it as the audio under the launch GIF/Reel in a video editor.

    python scripts/make_launch_audio.py [INPUT_WAV] [OUT_WAV]

Defaults: input out/song3_master.wav (your own material — safe to publish),
output out/keel_instagram_audio.wav. The test masters are NOT in the repo;
render one first (build.py) or pass a path. Needs numpy + soundfile.
"""

import sys

import numpy as np
import soundfile as sf

IN = sys.argv[1] if len(sys.argv) > 1 else "out/song3_master.wav"
OUT = sys.argv[2] if len(sys.argv) > 2 else "out/keel_instagram_audio.wav"
WIN = 18.0       # excerpt length (seconds)
HOP = 0.5        # search hop (seconds)
FADE = 0.4       # fade in/out (seconds)
SKIP_HEAD = 5.0  # don't start the excerpt in the first N seconds
SKIP_TAIL = 3.0  # ...or within N seconds of the end


def main():
    data, sr = sf.read(IN, always_2d=True)
    n = data.shape[0]
    dur = n / sr
    win = min(WIN, max(2.0, dur * 0.6))
    win_n = int(win * sr)

    mono = data.mean(axis=1)
    lo = int(min(SKIP_HEAD, dur * 0.1) * sr)
    hi = max(lo + 1, n - win_n - int(SKIP_TAIL * sr))

    best_start, best_rms = lo, -1.0
    step = max(1, int(HOP * sr))
    for s in range(lo, hi, step):
        seg = mono[s:s + win_n]
        rms = float(np.sqrt(np.mean(seg * seg)))
        if rms > best_rms:
            best_rms, best_start = rms, s

    clip = data[best_start:best_start + win_n].copy()
    f = int(FADE * sr)
    if f > 0 and clip.shape[0] > 2 * f:
        ramp = np.linspace(0.0, 1.0, f)[:, None]
        clip[:f] *= ramp
        clip[-f:] *= ramp[::-1]

    sf.write(OUT, clip, sr, subtype="PCM_24")
    print(f"audio saved: {OUT}  sr={sr}  {clip.shape[0]/sr:0.1f}s  "
          f"from {best_start/sr:0.1f}s of {IN} ({dur:0.1f}s, {data.shape[1]}ch)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
