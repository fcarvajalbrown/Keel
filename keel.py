# Keel — automix + automaster engine.
# Copyright (C) 2026 Felipe Carvajal Brown
#
# Licensed under the GNU Affero General Public License v3.0 (see LICENSE).
# A commercial license is available — see COMMERCIAL-LICENSE.md
# or contact fcarvajalbrown@gmail.com.
"""
keel  —  the public library API (one import surface for every front-end).

Keel's DSP lives in the flat engine modules (`recipes` / `mixer` / `mastering`
/ `meters`); `build.py` is the CLI button on top of them. This module is the
single, stable entry point a GUI or VST/plugin imports so all front-ends drive
ONE core — the DSP is never forked per front-end (a locked project rule). It
only re-exports the engine's public surface; it adds no behavior of its own.

    import keel

    groups = keel.autodetect("my_song")                 # {file: label}
    recipe = keel.mix_recipe({"balance": {"synth": -4}}) # defaults + overrides
    keel.mix("my_song", recipe, "out/song_mix.wav", mapping=groups)
    keel.master("out/song_mix.wav",
                keel.master_recipe(keel.preset_master("streaming")),
                "out/song_master.wav")

Everything here is deterministic: same stems + same recipe -> identical output.
"""
# --- recipe / data layer -------------------------------------------------
from recipes import (
    STEMS,
    KNOWN_LABELS,
    STEM_ALIASES,
    DEFAULT_BALANCE,
    DEFAULT_PAN,
    DEFAULT_SPREAD,
    DEFAULT_CHAIN,
    DEFAULT_MASTER,
    PRESETS,
    DEFAULT_PRESET,
    mix_recipe,
    master_recipe,
    preset_master,
)

# --- mix engine ----------------------------------------------------------
from mixer import (
    mix,
    autodetect,
    group_files,
    INTERNAL_ANCHOR_LUFS,
    OTHER_LABEL,
)

# --- master engine -------------------------------------------------------
from mastering import master

# --- metering ------------------------------------------------------------
from meters import integrated_lufs, true_peak_db

__version__ = "0.5.0"

__all__ = [
    # data / recipes
    "STEMS", "KNOWN_LABELS", "STEM_ALIASES", "DEFAULT_BALANCE", "DEFAULT_PAN",
    "DEFAULT_SPREAD",
    "DEFAULT_CHAIN", "DEFAULT_MASTER", "PRESETS", "DEFAULT_PRESET",
    "mix_recipe", "master_recipe", "preset_master",
    # mix engine
    "mix", "autodetect", "group_files", "INTERNAL_ANCHOR_LUFS", "OTHER_LABEL",
    # master engine
    "master",
    # metering
    "integrated_lufs", "true_peak_db",
    # meta
    "__version__",
]
