# Keel — automix + automaster engine.
# Copyright (C) 2026 Felipe Carvajal Brown
#
# Licensed under the GNU Affero General Public License v3.0 (see LICENSE).
# A commercial license is available — see COMMERCIAL-LICENSE.md
# or contact fcarvajalbrown@gmail.com.
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

# Labels are ARBITRARY — a project can have any number of stems and any labels.
# STEM_ALIASES is only the auto-detect HINT table: when Keel first scans a folder
# it guesses a label per file case-insensitively from these aliases (e.g.
# "vox.wav" -> "vocals"), writes them into keel.json, and the user edits from
# there. Anything unmatched is labelled "other". These known labels also seed
# DEFAULT_BALANCE; custom labels just default to 0.0 until the user sets them.
# The known/default labels (also the GUI's instrument dropdown — see KNOWN_LABELS
# below). Ordered roughly front-to-back of a rock arrangement.
STEMS = ["vocals", "backing", "drums", "perc", "bass", "guitar",
         "piano", "keys", "synth"]

# The single source of truth for the GUI's per-file instrument dropdown, so the
# UI choices can never drift from the engine's known set. The dropdown stays
# editable (custom labels allowed) — Keel is delivery-agnostic, any label works,
# unknowns fall to "other". STEM_ALIASES is only the auto-detect HINT table.
KNOWN_LABELS = STEMS

STEM_ALIASES = {
    # An alias matches when it is a PREFIX of a whole filename TOKEN (mixer.py
    # splits names on separators, camelCase, and letter/digit runs: "BassAmp1" ->
    # bass, amp; "01_Kick" -> kick; "ElecGtr2DT" -> elec, gtr, dt). Anchoring at a
    # token start is why short tokens are safe here: "oh" matches an overhead mic
    # "OH" but never "john", "hat" never "that" — a substring-in-filename match
    # could not tell them apart. Drum kits ship as per-component mics whose names
    # rarely contain "drum" (kick/snare/toms/overheads), so the kit-piece names are
    # listed to collapse a multi-mic kit into ONE drums group rather than scatter
    # it across "other". Aux percussion (tambourine/shaker/congas) is its OWN label
    # so it groups + balances apart from the kit; organ/keys is its own label apart
    # from synth pads. ORDER MATTERS: _match_label returns the first label with a
    # matching alias, so "backing" precedes "vocals" (a "backing vox" file must not
    # be caught as a lead vocal) and "guitar" precedes "vocals" (a "lead gtr" is a
    # guitar). Auto-detect is still only a first guess the user edits in keel.json;
    # the scan prints a mapping review so nothing is silently mislabeled.
    "drums":  ["drum", "drums", "kit", "kick", "kik", "snare", "snr",
               "tom", "toms", "cymbal", "crash", "ride", "hat", "hihat", "oh",
               "overhead"],
    "perc":   ["perc", "tamb", "shake", "conga", "bongo", "cowbell",
               "triangle", "cabasa", "woodblock"],
    "bass":   ["bass", "bs"],
    "guitar": ["guitar", "gtr", "gt"],
    "piano":  ["piano", "pno", "grand", "upright"],
    "keys":   ["keys", "key", "organ", "org", "hammond", "rhodes", "wurli",
               "wurlitzer", "epiano"],
    "synth":  ["synth", "syn", "pad"],
    "backing": ["backing", "bgv", "bvox", "harmony", "harmonies"],
    "vocals": ["vocals", "vocal", "vox", "voc", "lead"],
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
# New-instrument levels are research-backed (typical roles in a rock mix): keys /
# piano sit just under the guitars in a supporting role; backing vocals sit
# clearly under the lead (subtle doubles go lower — dial by hand); aux percussion
# is a quiet seasoning well below the kit. All editable per song.
DEFAULT_BALANCE = {
    "vocals":  0.0,
    "backing": -4.0,
    "drums":  -2.0,
    "perc":   -8.0,
    "bass":   -3.0,
    "guitar": -3.5,
    "piano":  -4.0,
    "keys":   -5.0,
    "synth":  -6.0,
}

# Stereo placement, -1.0 (hard L) .. +1.0 (hard R). Equal-power pan in the engine.
# DEFAULT = all centered, because the stems already carry their printed stereo
# image (instruments + FX baked in). Only set a pan here if you deliberately want
# to nudge a mono/centered stem; otherwise leave the stems' own width intact.
DEFAULT_PAN = {
    "vocals":  0.0,
    "backing": 0.0,
    "drums":   0.0,
    "perc":    0.0,
    "bass":    0.0,
    "guitar":  0.0,
    "piano":   0.0,
    "keys":    0.0,
    "synth":   0.0,
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
    "vocals":  {},
    "backing": {},
    "drums":   {},
    "perc":    {},
    "bass":    {},
    "guitar":  {},
    "piano":   {},
    "keys":    {},
    "synth":   {},
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

# ------------------------------------------------------------- MASTER PRESETS
# Named "house sound" loudness profiles. A preset only sets the master loudness
# target + true-peak ceiling — it picks how LOUD the master lands, not how the
# instruments sit, so balance/pan/spread are untouched. Selected at render time
# with `build.py --preset NAME`, which overrides keel.json's master block (an
# explicit --lufs / --tp still wins over the preset). The true-peak ceiling stays
# -1.0 dBTP across all three: streaming services recommend keeping true peaks
# at/under -1 dBTP so lossy transcoding (AAC/Ogg) doesn't clip. The targets are
# platform loudness-normalization references, not arbitrary numbers:
#   streaming  -14 LUFS  Spotify / YouTube / Tidal / Amazon normalize to here.
#   loud       -10 LUFS  club / aggressive; Keel's oversampled soft-clip + true-
#                        peak limiter hold this cleanly (see locked DSP note).
#                        On streaming it's turned down ~4 LU but keeps headroom.
#   broadcast  -16 LUFS  Apple Music / Apple Podcasts / AES TD1008 — quieter,
#                        more dynamic delivery (every -1 LUFS buys headroom).
# (EBU R128 TV/radio broadcast is the much quieter -23 LUFS; add a preset for it
# if a delivery ever calls for it.)
DEFAULT_PRESET = "streaming"

PRESETS = {
    "streaming": {"target_lufs": -14.0, "tp_ceiling_db": -1.0},
    "loud":      {"target_lufs": -10.0, "tp_ceiling_db": -1.0},
    "broadcast": {"target_lufs": -16.0, "tp_ceiling_db": -1.0},
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


def preset_master(name):
    """Return the master overrides ({target_lufs, tp_ceiling_db}) for a named
    preset, as a fresh copy. Raises ValueError naming the valid presets on an
    unknown name, so the CLI can surface a helpful message."""
    try:
        return dict(PRESETS[name])
    except KeyError:
        raise ValueError(
            f"unknown preset {name!r}; choose one of: "
            f"{', '.join(sorted(PRESETS))}")
