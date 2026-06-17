"""Render the Keel LinkedIn cover image from the SVG logo.

Draws the vector logo centered on a 1920x1080 black canvas and writes a PNG.
Regenerate the cover whenever the logo changes:

    python scripts/make_linkedin_cover.py

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
OUT = "assets/keel-cover-linkedin.png"
W, H = 1920, 1080
LOGO_ASPECT = 440.0 / 150.0  # logo native width:height
LOGO_WIDTH = 1180.0          # rendered logo width on the canvas


def main() -> int:
    app = QGuiApplication(sys.argv)  # noqa: F841 - required to init Qt paint stack

    img = QImage(W, H, QImage.Format_ARGB32)
    img.fill(QColor("#000000"))

    painter = QPainter(img)
    painter.setRenderHint(QPainter.Antialiasing, True)

    renderer = QSvgRenderer(LOGO)
    lh = LOGO_WIDTH / LOGO_ASPECT
    renderer.render(painter, QRectF((W - LOGO_WIDTH) / 2, (H - lh) / 2, LOGO_WIDTH, lh))
    painter.end()

    ok = img.save(OUT, "PNG")
    print(f"cover saved: {ok} {OUT} {W}x{H}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
