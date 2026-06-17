"""Render a tight black-background header logo for the README.

The Keel SVG logo centered on solid black with only a thin even margin (unlike
the 16:9 LinkedIn cover, which has lots of empty black). Regenerate when the
logo changes:

    python scripts/make_readme_header.py

Requires the GUI deps (PySide6); install with `setup.ps1 -Gui`. Run from the
repo root so the relative asset paths resolve.
"""

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QRectF
from PySide6.QtGui import QGuiApplication, QImage, QPainter, QColor
from PySide6.QtSvg import QSvgRenderer

LOGO = "assets/keel-logo.svg"
OUT = "assets/keel-logo-black.png"
# The SVG viewBox is 0 0 440 150 but the artwork doesn't fill it (empty space,
# mostly on the right and bottom). Crop to the content's bounding box so the
# black border ends up even on all sides. (x, y, w, h in SVG units.)
CONTENT_BOX = (6.0, 13.0, 376.0, 108.0)
LOGO_WIDTH = 1100.0  # rendered content width in px
MARGIN = 70.0        # thin even black border around the logo, in px


def main() -> int:
    app = QGuiApplication(sys.argv)  # noqa: F841 - required to init Qt paint stack

    cx, cy, cw, ch = CONTENT_BOX
    lw = LOGO_WIDTH
    lh = lw * ch / cw
    w = int(lw + 2 * MARGIN)
    h = int(lh + 2 * MARGIN)

    img = QImage(w, h, QImage.Format_ARGB32)
    img.fill(QColor("#000000"))

    painter = QPainter(img)
    painter.setRenderHint(QPainter.Antialiasing, True)
    renderer = QSvgRenderer(LOGO)
    renderer.setViewBox(QRectF(cx, cy, cw, ch))  # crop to the content
    renderer.render(painter, QRectF(MARGIN, MARGIN, lw, lh))
    painter.end()

    ok = img.save(OUT, "PNG")
    print(f"header saved: {ok} {OUT} {w}x{h}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
