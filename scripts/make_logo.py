"""Regenerate the Keel logo with the wordmark set in Space Grotesk.

Keeps the teal hull+waveform mark and the brand gradient verbatim, but redraws
the "Keel" wordmark (Space Grotesk Bold) and the "automatic mix + master"
tagline (Space Grotesk Regular) as OUTLINED SVG paths -- so the logo stays
font-independent (GitHub/installers don't need the font installed) yet matches
the standalone GUI, which uses Space Grotesk live.

Outputs:
    assets/keel-logo.svg         (vector, outlined)
    assets/keel-logo.png         (transparent, alpha-cropped)
    assets/keel-logo-black.png   (black background, README header) via the
                                 existing scripts/make_readme_header.py

Regenerate when the wordmark/font changes:

    .venv\\Scripts\\python.exe scripts/make_logo.py

Requires the GUI deps (PySide6); install with `setup.ps1 -Gui`. Run from the
repo root so the relative asset paths resolve.
"""
import io
import os
import subprocess
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
from PySide6.QtCore import QBuffer, QByteArray, QRectF, QRect
from PySide6.QtGui import (
    QFont, QFontDatabase, QGuiApplication, QImage, QPainter, QPainterPath,
    QTransform,
)
from PySide6.QtSvg import QSvgRenderer

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "assets" / "fonts"
SVG_OUT = ROOT / "assets" / "keel-logo.svg"
PNG_OUT = ROOT / "assets" / "keel-logo.png"
ICO_OUT = ROOT / "assets" / "keel.ico"      # Windows app icon (hull mark)
ICON_PNG_OUT = ROOT / "assets" / "keel-icon.png"   # square mark, for macOS/web

WORDMARK = "Keel"
TAGLINE = "automatic mix + master"
WORDMARK_FILL = "#15A99A"   # solid teal, matches the previous wordmark
TAGLINE_FILL = "#5FA8A1"    # muted teal, matches the previous tagline

# Footprint each text block must occupy in SVG (viewBox 0 0 440 150) units, so
# the new wordmark drops into the same place as the old one. (left, top, height)
WORDMARK_BOX = (155.77, 35.58, 50.42)
TAGLINE_BOX = (155.77, 104.66, 15.59)

# The hull mark + gradient, copied verbatim from the original logo.
HULL_SVG = """  <defs>
    <linearGradient id="teal" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#27D2C0"/>
      <stop offset="1" stop-color="#0C8C81"/>
    </linearGradient>
    <clipPath id="hull">
      <path d="M8,18 L28,96 Q60,120 92,96 L112,18 Z"/>
    </clipPath>
  </defs>

  <!-- waveform inside the hull (symmetric bell = a balanced, level hull) -->
  <g clip-path="url(#hull)" fill="url(#teal)">
    <rect x="56.5" y="30" width="7" height="80" rx="3.5"/>
    <rect x="45.5" y="40" width="7" height="70" rx="3.5"/>
    <rect x="67.5" y="40" width="7" height="70" rx="3.5"/>
    <rect x="34.5" y="52" width="7" height="58" rx="3.5"/>
    <rect x="78.5" y="52" width="7" height="58" rx="3.5"/>
    <rect x="23.5" y="66" width="7" height="44" rx="3.5"/>
    <rect x="89.5" y="66" width="7" height="44" rx="3.5"/>
  </g>

  <!-- hull outline (open top) -->
  <path d="M8,18 L28,96 Q60,120 92,96 L112,18" fill="none" stroke="url(#teal)"
        stroke-width="9" stroke-linecap="round" stroke-linejoin="round"/>"""


def _load_family():
    family = None
    for ttf in ("SpaceGrotesk-Regular.ttf", "SpaceGrotesk-Medium.ttf",
                "SpaceGrotesk-Bold.ttf"):
        fid = QFontDatabase.addApplicationFont(str(FONTS / ttf))
        if fid != -1 and family is None:
            fams = QFontDatabase.applicationFontFamilies(fid)
            if fams:
                family = fams[0]
    if not family:
        raise SystemExit("Space Grotesk not found in assets/fonts/")
    return family


def _path_to_d(path):
    """Convert a QPainterPath (glyph outlines) to an SVG path 'd' string."""
    ET = QPainterPath.ElementType
    out, i, n = [], 0, path.elementCount()
    while i < n:
        e = path.elementAt(i)
        if e.type == ET.MoveToElement:
            if out:
                out.append("Z")
            out.append(f"M{e.x:.2f},{e.y:.2f}")
            i += 1
        elif e.type == ET.LineToElement:
            out.append(f"L{e.x:.2f},{e.y:.2f}")
            i += 1
        elif e.type == ET.CurveToElement:
            c1, c2, ep = e, path.elementAt(i + 1), path.elementAt(i + 2)
            out.append(f"C{c1.x:.2f},{c1.y:.2f} {c2.x:.2f},{c2.y:.2f} "
                       f"{ep.x:.2f},{ep.y:.2f}")
            i += 3
        else:
            i += 1
    if out:
        out.append("Z")
    return " ".join(out)


def _text_path_d(family, text, weight, box):
    """Outline `text` and map its ink bounding box onto `box` (left, top, h)."""
    f = QFont(family)
    f.setPixelSize(200)            # large for precision; remapped below
    f.setWeight(weight)
    p = QPainterPath()
    p.addText(0.0, 0.0, f, text)
    bb = p.boundingRect()
    left, top, target_h = box
    s = target_h / bb.height()     # uniform scale to match the box height
    t = QTransform()
    t.translate(left, top)
    t.scale(s, s)
    t.translate(-bb.left(), -bb.top())
    return _path_to_d(t.map(p))


def _build_svg(family):
    wd = _text_path_d(family, WORDMARK, QFont.Bold, WORDMARK_BOX)
    td = _text_path_d(family, TAGLINE, QFont.Normal, TAGLINE_BOX)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 440 150" role="img"
     aria-label="Keel — Automatic Mixing + Mastering for Finished Stems">
{HULL_SVG}

  <!-- wordmark (Space Grotesk Bold) + tagline (Space Grotesk Regular), outlined -->
  <path d="{wd}" fill="{WORDMARK_FILL}"/>
  <path d="{td}" fill="{TAGLINE_FILL}"/>
</svg>
"""


def _render_png_cropped(svg_path, png_path, scale=4.0, pad=6):
    """Render the SVG to a transparent PNG, cropped to its ink bounding box."""
    r = QSvgRenderer(str(svg_path))
    vb = r.viewBoxF()
    w, h = int(vb.width() * scale), int(vb.height() * scale)
    img = QImage(w, h, QImage.Format_ARGB32)
    img.fill(0)
    pr = QPainter(img)
    r.render(pr, QRectF(0, 0, w, h))
    pr.end()

    ptr = img.constBits()
    arr = np.frombuffer(ptr, np.uint8).reshape(h, w, 4)
    alpha = arr[:, :, 3]
    ys, xs = np.where(alpha > 0)
    if len(xs) == 0:
        raise SystemExit("rendered logo is empty")
    x0, x1 = max(0, xs.min() - pad), min(w, xs.max() + 1 + pad)
    y0, y1 = max(0, ys.min() - pad), min(h, ys.max() + 1 + pad)
    img.copy(QRect(x0, y0, x1 - x0, y1 - y0)).save(str(png_path))
    return (x1 - x0, y1 - y0)


# The hull mark alone, framed square -- used as the app/window icon.
_ICON_SVG = (f'<svg xmlns="http://www.w3.org/2000/svg" '
             f'viewBox="-4.5 4.5 129 129">\n{HULL_SVG}\n</svg>\n')


def _render_app_icon(ico_path, png_path, size=256):
    """Render the square hull mark and write a multi-size Windows .ico + a PNG."""
    from PIL import Image
    r = QSvgRenderer(QByteArray(_ICON_SVG.encode("utf-8")))
    img = QImage(size, size, QImage.Format_ARGB32)
    img.fill(0)
    pr = QPainter(img)
    pr.setRenderHint(QPainter.Antialiasing)
    r.render(pr, QRectF(0, 0, size, size))
    pr.end()
    img.save(str(png_path))

    ba = QByteArray()
    buf = QBuffer(ba)
    buf.open(QBuffer.WriteOnly)
    img.save(buf, "PNG")
    buf.close()
    im = Image.open(io.BytesIO(bytes(ba.data()))).convert("RGBA")
    im.save(str(ico_path),
            sizes=[(256, 256), (128, 128), (64, 64), (48, 48),
                   (32, 32), (16, 16)])


def main():
    app = QGuiApplication(sys.argv)  # noqa: F841 - inits the Qt paint stack
    family = _load_family()
    SVG_OUT.write_text(_build_svg(family), encoding="utf-8")
    print(f"wrote {SVG_OUT}")
    size = _render_png_cropped(SVG_OUT, PNG_OUT)
    print(f"wrote {PNG_OUT}  ({size[0]}x{size[1]})")
    _render_app_icon(ICO_OUT, ICON_PNG_OUT)
    print(f"wrote {ICO_OUT} + {ICON_PNG_OUT}")

    # refresh the black-background README header from the new SVG
    header = ROOT / "scripts" / "make_readme_header.py"
    if header.exists():
        subprocess.run([sys.executable, str(header)], cwd=str(ROOT), check=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
