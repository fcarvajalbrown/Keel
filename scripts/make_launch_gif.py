"""Render the Keel launch GIF (9:16, Spanish on-screen text) for Instagram.

A short looping animation:
  1. logo reveal + tagline ("Gratis. Abierta. Determinista.")
  2. the logo's own 7-bar waveform settles from uneven into a balanced "bell"
     while the integrated-loudness readout counts up to -14.0 LUFS
  3. a "download free" end card with the repo URL and platforms.

Output: assets/keel-launch.gif  (9:16, 720x1280). For a higher-quality Reel,
convert the GIF to MP4 (e.g. in CapCut) — GIF keeps file size sane here.

Requires PySide6 + Pillow. Run from the repo root.
"""

import io
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QRectF, QBuffer, QByteArray, Qt
from PySide6.QtGui import (QGuiApplication, QImage, QPainter, QColor, QFont,
                           QFontDatabase)
from PySide6.QtSvg import QSvgRenderer
from PIL import Image

# Offscreen Qt does not always resolve a system font, drawing tofu boxes for
# live text. Load a real font file up front and use its family everywhere.
FONT_FAMILY = "Arial"
FONT_CANDIDATES = [
    r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\arialbd.ttf",
    r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\seguisb.ttf",
]


def load_fonts():
    global FONT_FAMILY
    fam = None
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            fid = QFontDatabase.addApplicationFont(path)
            fams = QFontDatabase.applicationFontFamilies(fid)
            if fams and fam is None:
                fam = fams[0]
    if fam:
        FONT_FAMILY = fam

W, H = 720, 1280
FPS = 12
OUT = "assets/keel-launch.gif"
LOGO = "assets/keel-logo.svg"
LOGO_BOX = (6.0, 13.0, 376.0, 108.0)  # content bbox in SVG units (see make_readme_header)

TEAL = QColor("#27D2C0")
TEAL_DK = QColor("#15A99A")
MUTED = QColor("#5FA8A1")
WHITE = QColor("#F2FFFD")
GREEN = QColor("#2EA44F")
BLACK = QColor("#000000")

# the logo's waveform bar heights (a symmetric, balanced bell) and an uneven start
BELL = [44, 58, 70, 80, 70, 58, 44]
START = [74, 28, 86, 22, 64, 38, 70]


def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)  # smoothstep


def lerp(a, b, t):
    return a + (b - a) * t


def font(px, bold=True):
    f = QFont(FONT_FAMILY)
    f.setPixelSize(int(px))
    f.setBold(bold)
    return f


def draw_logo(p, cx, cy, w, opacity=1.0):
    cbx, cby, cbw, cbh = LOGO_BOX
    h = w * cbh / cbw
    p.save()
    p.setOpacity(opacity)
    r = QSvgRenderer(LOGO)
    r.setViewBox(QRectF(cbx, cby, cbw, cbh))
    r.render(p, QRectF(cx - w / 2, cy - h / 2, w, h))
    p.restore()


def draw_bars(p, heights, cx, baseline, unit=70, gap=14, color=TEAL):
    n = len(heights)
    bw = unit
    total = n * bw + (n - 1) * gap
    x = cx - total / 2
    p.setPen(Qt.NoPen)
    p.setBrush(color)
    for hgt in heights:
        bar_h = hgt / 80.0 * 320
        rect = QRectF(x, baseline - bar_h, bw, bar_h)
        p.drawRoundedRect(rect, bw / 2, bw / 2)
        x += bw + gap


def text(p, s, y, px, color=WHITE, bold=True, x=None, w=None):
    p.setFont(font(px, bold))
    p.setPen(color)
    if x is None:
        x, w = 0, W
    p.drawText(QRectF(x, y, w, px * 1.6), Qt.AlignHCenter | Qt.AlignTop, s)


def render_frame(i, total):
    img = QImage(W, H, QImage.Format_RGB888)
    img.fill(BLACK)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setRenderHint(QPainter.TextAntialiasing, True)

    t = i / FPS  # seconds

    # ---- Scene A: logo reveal (0.0 - 2.4s) ----
    if t < 2.4:
        rev = ease(t / 0.9)
        scale = lerp(0.86, 1.0, rev)
        draw_logo(p, W / 2, H * 0.42, 600 * scale, opacity=rev)
        if t > 1.1:
            text(p, "Gratis · Abierta · Determinista", H * 0.58,
                 40, MUTED, bold=True)
        if t > 1.6:
            text(p, "mezcla + masterización automática", H * 0.62,
                 30, TEAL_DK, bold=False)

    # ---- Scene B: balance + loudness (2.4 - 6.8s) ----
    elif t < 6.8:
        u = (t - 2.4) / 4.4
        e = ease(u)
        text(p, "Balance + master,", H * 0.09, 56, WHITE)
        text(p, "en un clic", H * 0.09 + 66, 56, TEAL)

        lufs = lerp(-22.0, -14.0, e)
        text(p, f"{lufs:0.1f}", H * 0.30, 150, TEAL)
        text(p, "LUFS integrados", H * 0.30 + 172, 38, MUTED, bold=False)
        if t > 4.6:
            text(p, "true peak -1.0 dBTP · sin clipping", H * 0.49,
                 32, MUTED, bold=False)

        heights = [lerp(s, b, e) for s, b in zip(START, BELL)]
        draw_bars(p, heights, W / 2, H * 0.86)

    # ---- Scene C: end card (6.8 - end) ----
    else:
        draw_logo(p, W / 2, H * 0.30, 560)
        text(p, "Descárgalo gratis", H * 0.46, 60, WHITE)
        # a faux download button
        bw, bh = 470, 96
        bx, by = (W - bw) / 2, H * 0.55
        p.setPen(Qt.NoPen)
        p.setBrush(GREEN)
        p.drawRoundedRect(QRectF(bx, by, bw, bh), 16, 16)
        text(p, "DESCARGAR", by + 20, 42, WHITE)
        text(p, "github.com/fcarvajalbrown/Keel", H * 0.66, 34, TEAL_DK, bold=True)
        text(p, "código abierto · sin IA · sin suscripción", H * 0.71,
             30, MUTED, bold=False)

    # thin progress bar along the bottom. Doubles as a story-progress cue AND
    # makes every frame unique, so Pillow can't merge static "hold" frames
    # (which gives them long per-frame delays that many video editors ignore,
    # collapsing the clip to ~6s). Unique frames => all 108 stored => full ~9s.
    prog = (i + 1) / total
    p.setPen(Qt.NoPen)
    p.setBrush(TEAL)
    p.drawRect(QRectF(0, H - 8, W * prog, 8))

    p.end()

    ba = QByteArray()            # keep alive: QBuffer holds a pointer to it
    buf = QBuffer(ba)
    buf.open(QBuffer.ReadWrite)
    img.save(buf, "PNG")
    buf.close()
    pil = Image.open(io.BytesIO(bytes(ba))).convert("RGB")
    return pil


def main():
    app = QGuiApplication(sys.argv)  # noqa: F841 - init Qt paint stack
    load_fonts()
    total = int(9.0 * FPS)
    frames = [render_frame(i, total) for i in range(total)]
    frames[0].save(
        OUT, save_all=True, append_images=frames[1:],
        duration=int(1000 / FPS), loop=0, optimize=True,
    )
    size = os.path.getsize(OUT)
    print(f"gif saved: {OUT}  {W}x{H}  {total} frames  {size/1_000_000:.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
