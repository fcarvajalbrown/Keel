# -*- mode: python ; coding: utf-8 -*-
# Keel.spec — PyInstaller build config for the desktop GUI (gui.py).
#
#   Windows:  a single onefile  dist/Keel.exe        (easy to hand around)
#   macOS:    a onedir  dist/Keel.app  bundle        (CI wraps it in Keel.dmg)
#
# macOS uses onedir + BUNDLE on purpose: onefile inside a .app is deprecated
# (blocked in PyInstaller 7) and penalised by macOS security scanning. Windows
# onefile is fine. Build with:  pyinstaller Keel.spec --noconfirm
import sys
from pathlib import Path

IS_MAC = sys.platform == "darwin"

# The engine modules gui.py reaches through `import keel` (which pulls in the
# rest). Listed explicitly so a frozen build never misses one.
ENGINE = ["keel", "recipes", "mixer", "mastering", "meters", "build",
          "userpresets", "gui_theme"]

# Bundled UI assets: the Space Grotesk font (SIL OFL) + its license. gui_theme
# resolves these via sys._MEIPASS at runtime, so they must land at assets/fonts.
DATAS = [(str(p), "assets/fonts")
         for p in Path("assets/fonts").glob("*.ttf")]
DATAS += [("assets/fonts/OFL.txt", "assets/fonts")]

a = Analysis(
    ["gui.py"],
    pathex=[],
    binaries=[],
    datas=DATAS,
    hiddenimports=ENGINE,
    hookspath=[],
    runtime_hooks=[],
    # matchering (optional reference-master path) is a huge numba/llvmlite tree
    # and isn't used by the GUI scaffold; tkinter is unused. Exclude to slim.
    excludes=["matchering", "tkinter"],
    noarchive=False,
)
pyz = PYZ(a.pure)

if IS_MAC:
    exe = EXE(
        pyz, a.scripts, [],
        exclude_binaries=True,
        name="Keel",
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=True,   # let macOS file-open events reach the app
        target_arch=None,
    )
    coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="Keel")
    app = BUNDLE(
        coll,
        name="Keel.app",
        icon=None,
        bundle_identifier="com.felipecarvajalbrown.keel",
        info_plist={"NSHighResolutionCapable": True},
    )
else:
    exe = EXE(
        pyz, a.scripts, a.binaries, a.datas, [],
        name="Keel",
        console=False,        # windowed GUI app, no console window
        strip=False,
        upx=False,
        runtime_tmpdir=None,
        icon="assets/keel.ico",   # Keel hull mark instead of the default icon
    )
