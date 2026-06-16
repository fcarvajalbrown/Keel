# Keel — automix + automaster engine.
# Copyright (C) 2026 Felipe Carvajal Brown
#
# Licensed under the GNU Affero General Public License v3.0 (see LICENSE).
# A commercial license is available — see COMMERCIAL-LICENSE.md
# or contact fcarvajalbrown@gmail.com.
"""
userpresets.py  —  user-saved master loudness presets (a tiny JSON store).

The built-in house sounds live in `recipes.PRESETS` (read-only). This adds a
small editable layer on top so a front-end (the GUI) can save/load named
loudness profiles the user creates, without touching the engine's defaults. A
preset is the same shape as a built-in one: {"target_lufs": ..., "tp_ceiling_db":
...}. Stored as `userpresets.json` next to the code; it is user data, gitignored.
"""
import json
from pathlib import Path

import recipes

STORE = Path(__file__).resolve().parent / "userpresets.json"


def load_user_presets():
    """Return the user's saved presets as {name: master_dict} (empty if none)."""
    if STORE.exists():
        try:
            data = json.loads(STORE.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (ValueError, OSError):
            return {}
    return {}


def save_user_preset(name, master):
    """Add/overwrite a user preset and persist. `master` is
    {target_lufs, tp_ceiling_db}. Returns the full user-preset map."""
    name = str(name).strip()
    if not name:
        raise ValueError("preset name cannot be empty")
    if name in recipes.PRESETS:
        raise ValueError(f"{name!r} is a built-in preset; choose another name")
    presets = load_user_presets()
    presets[name] = {
        "target_lufs": float(master["target_lufs"]),
        "tp_ceiling_db": float(master["tp_ceiling_db"]),
    }
    STORE.write_text(json.dumps(presets, indent=2) + "\n", encoding="utf-8")
    return presets


def delete_user_preset(name):
    """Remove a user preset if present and persist. Returns the updated map."""
    presets = load_user_presets()
    presets.pop(name, None)
    STORE.write_text(json.dumps(presets, indent=2) + "\n", encoding="utf-8")
    return presets


def all_presets():
    """Built-in presets overlaid with the user's (user names can't shadow a
    built-in — save_user_preset forbids it). Ordered: built-ins, then user."""
    merged = dict(recipes.PRESETS)
    merged.update(load_user_presets())
    return merged
