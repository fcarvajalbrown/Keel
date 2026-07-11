# Keel — automix + automaster engine.
# Copyright (C) 2026 Felipe Carvajal Brown
#
# Licensed under the GNU Affero General Public License v3.0 (see LICENSE).
# A commercial license is available — see COMMERCIAL-LICENSE.md
# or contact fcarvajalbrown@gmail.com.
"""
encode.py  —  DELIVERY-FORMAT EXPORT (transcode the finished master).

Keel's guaranteed-spec deliverable is the PCM WAV the master engine writes. This
module transcodes THAT file into the extra delivery formats a musician actually
uploads, without re-running any DSP: the master is the single source, every
format is a faithful copy of it.

  FLAC  — lossless. Bit-exact to the master (part of the byte-identical promise).
  MP3   — lossy, via libsndfile's built-in LAME (MPEG Layer III).
  OGG   — lossy, Vorbis, via libsndfile.
  AAC   — lossy, in an .m4a container, via ffmpeg (bundled imageio-ffmpeg if
          present, else a system ffmpeg). Only format needing an external tool.

Determinism: FLAC is bit-exact. The lossy formats are deterministic *given the
same encoder version* but are explicitly NOT part of Keel's byte-identical
guarantee — that promise stays a PCM/WAV promise. Unknown or unavailable formats
raise a clear, user-facing error rather than silently skipping.

No DAW project/session files are written (a standing non-goal) — audio only.
"""
import shutil
import subprocess
from pathlib import Path

import soundfile as sf

import meters

# libsndfile-native targets: no external tool needed (offline-clean). Each maps to
# a (soundfile format, subtype-or-None) — None means "follow the master's depth".
_SF_FORMATS = {
    "wav":  ("WAV", None),
    "flac": ("FLAC", None),          # lossless; subtype follows the master depth
    "ogg":  ("OGG", "VORBIS"),
    "mp3":  ("MP3", "MPEG_LAYER_III"),
}
# targets that require ffmpeg (libsndfile has no AAC encoder).
_FFMPEG_FORMATS = {
    "aac": ("m4a", ["-c:a", "aac"]),
    "m4a": ("m4a", ["-c:a", "aac"]),
}

# lossless targets (bit-exact to the master) vs lossy.
_LOSSLESS = {"wav", "flac"}


def ffmpeg_exe():
    """Path to an ffmpeg binary, or None. Prefers the bundled imageio-ffmpeg (so
    AAC works offline once that optional wheel is present), then a system ffmpeg."""
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return shutil.which("ffmpeg")


def available_formats():
    """The delivery formats this machine can produce right now. WAV/FLAC/OGG/MP3
    are always available (libsndfile); AAC/M4A only if an ffmpeg is found."""
    fmts = set(_SF_FORMATS)
    if ffmpeg_exe():
        fmts |= set(_FFMPEG_FORMATS)
    return fmts


def parse_formats(spec):
    """Parse a '--format flac,mp3' spec into a clean, de-duplicated list, dropping
    a bare 'wav' (the master already IS the WAV). Raises ValueError naming any
    unknown format, or an available one that needs a tool this machine lacks."""
    known = set(_SF_FORMATS) | set(_FFMPEG_FORMATS)
    out, seen = [], set()
    for raw in (spec or "").split(","):
        f = raw.strip().lower()
        if not f or f == "wav":
            continue
        if f not in known:
            raise ValueError(
                f"unknown export format {f!r}; choose from: "
                f"{', '.join(sorted(known - {'wav'}))}")
        if f in _FFMPEG_FORMATS and not ffmpeg_exe():
            raise ValueError(
                f"{f!r} export needs ffmpeg (install imageio-ffmpeg or put "
                f"ffmpeg on PATH); WAV/FLAC/OGG/MP3 need no external tool.")
        if f not in seen:
            seen.add(f)
            out.append(f)
    return out


def _flac_subtype(master_subtype):
    """FLAC keeps the master's integer depth (16/24). A float master (32) has no
    FLAC integer equivalent that stays exact, so it stores at 24-bit."""
    return master_subtype if master_subtype in ("PCM_16", "PCM_24") else "PCM_24"


def measure_true_peak(path):
    """4x-oversampled true-peak (dBTP) of a rendered/encoded file — decode it and
    meter it exactly as the master was metered (meters.true_peak_db).

    libsndfile decodes WAV/FLAC/MP3/OGG directly. AAC/M4A it can't decode, so we
    fall back to ffmpeg: transcode to a temporary float WAV, meter that, discard
    it. (The ffmpeg that produced the AAC is by definition present here.)"""
    try:
        audio, rate = sf.read(str(path), dtype="float32", always_2d=True)
    except sf.LibsndfileError:
        exe = ffmpeg_exe()
        if not exe:
            raise
        import tempfile
        tmpdir = tempfile.mkdtemp(prefix="keel_tp_")
        tmp = Path(tmpdir) / "decode.wav"
        subprocess.run([exe, "-y", "-hide_banner", "-loglevel", "error",
                        "-i", str(path), "-c:a", "pcm_f32le", str(tmp)],
                       check=True, stdout=subprocess.DEVNULL,
                       stderr=subprocess.PIPE)
        try:
            audio, rate = sf.read(str(tmp), dtype="float32", always_2d=True)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    return meters.true_peak_db(audio, rate)


def verify_true_peak(path, tp_ceiling_db):
    """Re-measure a delivery file's true-peak AFTER encoding and grade it against
    the master's ceiling. Lossy transcoding (AAC/MP3/Ogg) reconstructs the
    waveform and can push intersample peaks ABOVE the master's — this is the read-
    only gate that makes 'Keel leaves headroom for transcoding' auditable rather
    than a claim. It NEVER reshapes the master; it only reports:

      PASS  post-codec true-peak stayed at/under the delivered ceiling.
      WARN  the codec ate into the headroom (over the ceiling) but did not clip.
      FAIL  post-codec true-peak went over 0 dBTP — it will clip on playback.
    """
    tp = measure_true_peak(path)
    clipped = bool(tp > 0.0) if (tp == tp) else False  # tp==tp guards -inf/NaN
    over_ceiling = bool(tp > tp_ceiling_db + 0.05) if (tp == tp) else False
    verdict = "FAIL" if clipped else ("WARN" if over_ceiling else "PASS")
    return {"ceiling_db": tp_ceiling_db,
            "post_tp_db": round(tp, 2) if (tp == tp) else tp,
            "over_ceiling": over_ceiling, "clipped": clipped,
            "verdict": verdict}


def encode_one(master_path, fmt, out_path, aac_bitrate="256k",
               tp_ceiling_db=None):
    """Transcode the master at `master_path` into a single `fmt` file at
    `out_path`. Returns a small info dict. Assumes `fmt` was validated by
    parse_formats (available + known)."""
    master_path, out_path = Path(master_path), Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if fmt in _SF_FORMATS:
        sf_format, subtype = _SF_FORMATS[fmt]
        if fmt == "flac":
            subtype = _flac_subtype(sf.info(str(master_path)).subtype)
        audio, rate = sf.read(str(master_path), dtype="float32", always_2d=True)
        sf.write(str(out_path), audio, rate, format=sf_format, subtype=subtype)
    else:  # ffmpeg AAC/M4A
        _container, codec_args = _FFMPEG_FORMATS[fmt]
        cmd = [ffmpeg_exe(), "-y", "-hide_banner", "-loglevel", "error",
               "-i", str(master_path), *codec_args, "-b:a", aac_bitrate,
               str(out_path)]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL,
                       stderr=subprocess.PIPE)
    info = {"format": fmt, "out": str(out_path),
            "lossless": fmt in _LOSSLESS,
            "bytes": out_path.stat().st_size if out_path.exists() else 0}
    if tp_ceiling_db is not None:
        info["tp_verify"] = verify_true_peak(out_path, tp_ceiling_db)
    return info


def _ext_for(fmt):
    """Filename extension for a format (AAC lands in an .m4a container)."""
    if fmt in _FFMPEG_FORMATS:
        return _FFMPEG_FORMATS[fmt][0]
    return fmt


def export(master_path, formats, out_dir, name, aac_bitrate="256k",
           tp_ceiling_db=None):
    """Transcode the master into every requested delivery format alongside it.
    `formats` is a validated list (see parse_formats). Writes
    <out_dir>/<name>.<ext> per format and returns a list of info dicts. When
    `tp_ceiling_db` is given, each file is decoded and true-peak-re-measured (an
    advisory PASS/WARN/FAIL gate — see verify_true_peak)."""
    results = []
    for fmt in formats:
        out_path = Path(out_dir) / f"{name}.{_ext_for(fmt)}"
        results.append(encode_one(master_path, fmt, out_path,
                                   aac_bitrate=aac_bitrate,
                                   tp_ceiling_db=tp_ceiling_db))
    return results
