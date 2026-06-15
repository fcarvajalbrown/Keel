"""
recipes.py  —  THE DATA LAYER (Keel's "recipe").

Declarative mix + master settings. A recipe says WHAT the result should be
(per-stem loudness balance, optional panning, master loudness + true-peak
ceiling, optional reference track). The engine (mixer.py / mastering.py) decides
HOW to render it.

Everything here is project-agnostic: edit the DEFAULT_* tables to change how Keel
balances and masters, then re-run build.py. Per-project tweaks are passed in as
small override dicts (see build.py) and deep-merged onto these defaults — you
never have to edit this file to mix a new song. Never hand-tweak the rendered
WAVs; they are build artifacts.
"""

# The 5 stem types Keel knows about. Stem files are matched case-insensitively by
# these names, with a few common aliases, so e.g. "vocals.wav", "vox.wav",
# "Vocal Guide.wav" all map to "vocals".
STEMS = ["drums", "bass", "guitar", "synth", "vocals"]

STEM_ALIASES = {
    "drums":  ["drum", "drums", "kit", "perc"],
    "bass":   ["bass", "bs"],
    "guitar": ["guitar", "gtr", "gt"],
    "synth":  ["synth", "syn", "pad", "keys"],
    "vocals": ["vocals", "vocal", "vox", "vocal guide", "voc", "lead"],
}

# Multiple files of one type are normal — double-tracked guitars (guitar_L.wav +
# guitar_R.wav) or a doubled vocal (vocals1.wav + vocals2.wav). The matcher
# collects ALL files of a type and the mixer balances them as one GROUP, so the
# loudness target applies to their sum: a doubled part hits its target without
# coming out twice as loud as a single one. The doubles' printed relationship
# (relative level + any baked-in panning) is preserved.

# ------------------------------------------------------------------ MIX DEFAULTS
# Relative loudness balance, in LU, measured against the vocal anchor (vocals=0).
# A balanced mix = all instruments at the intended *perceived* loudness, so the
# engine normalizes each stem to an internal anchor then applies these offsets.
# (Loudness-balancing approach — Ward/Reiss, "Multitrack mixing using a model of
# loudness and partial loudness".) More negative = quieter in the mix.
DEFAULT_BALANCE = {
    "vocals": 0.0,
    "drums": -2.0,
    "bass":  -3.0,
    "guitar": -3.5,
    "synth": -6.0,
}

# Stereo placement, -1.0 (hard L) .. +1.0 (hard R). Equal-power pan in the engine.
# DEFAULT = all centered, because the stems already carry their printed stereo
# image (instruments + FX baked in). Only set a pan here if you deliberately want
# to nudge a mono/centered stem; otherwise leave the stems' own width intact.
DEFAULT_PAN = {
    "vocals": 0.0,
    "drums":  0.0,
    "bass":   0.0,
    "guitar": 0.0,
    "synth":  0.0,
}

# Auto-spread for multi-file groups: if a type has >1 file AND spread > 0, its
# files are panned symmetrically across +/- spread (e.g. guitar 0.6 = doubles to
# ~hard L/R). DEFAULT 0 = respect the stems' OWN printed stereo image (the safe
# choice when width is already baked in). Set guitar spread only if the two
# guitars are delivered as dry mono dual-tracks meant to be panned here.
DEFAULT_SPREAD = {
    "guitar": 0.0,
    "vocals": 0.0,
}

# Per-stem processing chain (built-in pedalboard effects). EMPTY BY DEFAULT.
# Keel assumes the stems are already mixed-ready (virtual instruments +
# EQ/comp/reverb printed), so the mixer does NOT re-process tone — it only
# balances levels and sums. These fields exist as an escape hatch if a single
# stem ever needs a corrective move, but by default they stay empty so nothing is
# double-processed.
#   hpf:    highpass corner (Hz)         eq:     list of (freq, gain_db, q) bells
#   comp:   (threshold_db, ratio)        reverb: 0.0..1.0 wet mix
DEFAULT_CHAIN = {
    "drums":  {},
    "bass":   {},
    "guitar": {},
    "synth":  {},
    "vocals": {},
}

# ----------------------------------------------------------------- MASTER DEFAULTS
# Integrated loudness target. -14 LUFS = streaming-optimal (Spotify/YouTube/Apple
# normalize to roughly here, so louder just gets turned down anyway) and stays
# clean through Keel's limiter — no distortion. True-peak ceiling -1 dBTP. Go
# louder (e.g. -10/-11) when a track wants it; the oversampled soft-clip + true-
# peak limiter hold up cleanly.
DEFAULT_MASTER = {
    "target_lufs": -14.0,
    "tp_ceiling_db": -1.0,
    # If a reference master is provided, mastering.py uses Matchering against it
    # and IGNORES target_lufs (the reference sets loudness). Otherwise it falls
    # back to the internal EQ -> soft-clip -> limiter -> normalize chain.
    "reference": None,   # or a filename resolved against build.py's references dir
}


def _deep_merge(base, override):
    """Per-key merge; nested dicts merge, scalars/lists from override win."""
    out = {k: (dict(v) if isinstance(v, dict) else v) for k, v in base.items()}
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def mix_recipe(overrides=None):
    """Resolve a full per-stem mix recipe (DEFAULT_* + optional per-project
    overrides). `overrides` is a sparse dict like
    {"balance": {"synth": -4.5}, "pan": {...}, "spread": {...}, "chain": {...}}."""
    ov = overrides or {}
    return {
        "balance": _deep_merge(DEFAULT_BALANCE, ov.get("balance", {})),
        "pan":     _deep_merge(DEFAULT_PAN,     ov.get("pan", {})),
        "spread":  _deep_merge(DEFAULT_SPREAD,  ov.get("spread", {})),
        "chain":   _deep_merge(DEFAULT_CHAIN,   ov.get("chain", {})),
    }


def master_recipe(overrides=None):
    """Resolve a full master recipe (DEFAULT_MASTER + optional per-project
    overrides like {"target_lufs": -11.0, "reference": "ref.wav"})."""
    return _deep_merge(DEFAULT_MASTER, overrides or {})
