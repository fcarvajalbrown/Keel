"""Render the Keel launch video for Instagram (9:16, Spanish on-screen text).

A ~15 s seamless loop in four scenes:
  1. logo reveal + tagline ("Gratis. Abierta. Determinista.")
  2. stems -> mezcla + master (labeled chips converge to one master)
  3. the loudness meter counts to -14.0 LUFS as the waveform settles to a bell
  4. "Descárgalo gratis" end card, then fades back to black = the first frame,
     so it loops cleanly (replays compound Instagram watch time).

Outputs both:
  * assets/keel-launch.mp4  (1080x1920, H.264) -- for the video editor / Reel
  * assets/keel-launch.gif  (720x1280)         -- quick preview

Requires PySide6, Pillow, imageio + imageio-ffmpeg. Run from the repo root.
"""

import io
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QRectF, QBuffer, QByteArray, Qt
from PySide6.QtGui import (QGuiApplication, QImage, QPainter, QColor, QFont,
                           QFontDatabase, QPen)
from PySide6.QtSvg import QSvgRenderer
from PIL import Image
import numpy as np
import imageio.v2 as iio

W, H = 1080, 1920
FPS = 12
DUR = 15.0
MP4 = "assets/keel-launch.mp4"
GIF = "assets/keel-launch.gif"
GIF_SIZE = (720, 1280)
LOGO = "assets/keel-logo.svg"
LOGO_BOX = (6.0, 13.0, 376.0, 108.0)  # content bbox in SVG units

TEAL = QColor("#27D2C0")
TEAL_DK = QColor("#15A99A")
MUTED = QColor("#5FA8A1")
WHITE = QColor("#F2FFFD")
GREEN = QColor("#2EA44F")
BLACK = QColor("#000000")
CHIP_FILL = QColor(18, 38, 36)

BELL = [44, 58, 70, 80, 70, 58, 44]
START = [74, 28, 86, 22, 64, 38, 70]
CHIPS = ["drums", "bajo", "guitarra", "voz", "synth"]

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


def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * t


def font(px, bold=True):
    f = QFont(FONT_FAMILY)
    f.setPixelSize(int(px))
    f.setBold(bold)
    return f


def text(p, s, y, px, color=WHITE, bold=True):
    p.setFont(font(px, bold))
    p.setPen(color)
    p.drawText(QRectF(0, y, W, px * 1.6), Qt.AlignHCenter | Qt.AlignTop, s)


def draw_logo(p, cx, cy, w, opacity=1.0):
    cbx, cby, cbw, cbh = LOGO_BOX
    h = w * cbh / cbw
    p.save()
    p.setOpacity(opacity)
    r = QSvgRenderer(LOGO)
    r.setViewBox(QRectF(cbx, cby, cbw, cbh))
    r.render(p, QRectF(cx - w / 2, cy - h / 2, w, h))
    p.restore()


def draw_bars(p, heights, cx, baseline, unit=105, gap=21, color=TEAL):
    total = len(heights) * unit + (len(heights) - 1) * gap
    x = cx - total / 2
    p.setPen(Qt.NoPen)
    p.setBrush(color)
    for hgt in heights:
        bar_h = hgt / 80.0 * 480
        p.drawRoundedRect(QRectF(x, baseline - bar_h, unit, bar_h), unit / 2, unit / 2)
        x += unit + gap


def draw_chip(p, cx, cy, w, h, label, opacity):
    p.save()
    p.setOpacity(opacity)
    p.setPen(QPen(TEAL_DK, 3))
    p.setBrush(CHIP_FILL)
    p.drawRoundedRect(QRectF(cx - w / 2, cy - h / 2, w, h), h / 2, h / 2)
    p.setPen(WHITE)
    p.setFont(font(int(h * 0.44), True))
    p.drawText(QRectF(cx - w / 2, cy - h / 2, w, h), Qt.AlignCenter, label)
    p.restore()


def render_frame(i, total):
    img = QImage(W, H, QImage.Format_RGB888)
    img.fill(BLACK)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setRenderHint(QPainter.TextAntialiasing, True)
    t = i / FPS

    # ---- Scene A: logo reveal (0.0 - 3.0) ----
    if t < 3.0:
        rev = ease(t / 1.0)
        draw_logo(p, W / 2, H * 0.42, lerp(0.86, 1.0, rev) * 900, opacity=rev)
        if t > 1.3:
            text(p, "Gratis · Abierta · Determinista", H * 0.57, 58, MUTED)
        if t > 1.8:
            text(p, "mezcla + masterización automática", H * 0.61, 44, TEAL_DK, False)

    # ---- Scene B: stems -> master (3.0 - 6.5) ----
    elif t < 6.5:
        e = ease((t - 3.0) / 3.5)
        text(p, "De tus stems terminados", H * 0.08, 64, WHITE)
        top, cw, ch, gap = H * 0.20, 460, 88, 24
        for k, lab in enumerate(CHIPS):
            op = max(0.0, min(1.0, (e - k * 0.10) / 0.15))
            if op <= 0:
                continue
            cy = top + k * (ch + gap) + ch / 2
            draw_chip(p, W / 2 + (1 - op) * -40, cy, cw, ch, lab, op)
        if e > 0.6:
            text(p, "->  una mezcla y un máster", H * 0.70, 60, TEAL)

    # ---- Scene C: balance + loudness (6.5 - 11.5) ----
    elif t < 11.5:
        e = ease((t - 6.5) / 5.0)
        text(p, "Balance + master,", H * 0.085, 84, WHITE)
        text(p, "en un clic", H * 0.085 + 100, 84, TEAL)
        lufs = lerp(-22.0, -14.0, e)
        text(p, f"{lufs:0.1f}", H * 0.30, 225, TEAL)
        text(p, "LUFS integrados", H * 0.30 + 258, 57, MUTED, False)
        if t > 8.7:
            text(p, "true peak -1.0 dBTP · sin clipping", H * 0.49, 48, MUTED, False)
        heights = [lerp(s, b, e) for s, b in zip(START, BELL)]
        draw_bars(p, heights, W / 2, H * 0.86)

    # ---- Scene D: end card + fade to black (11.5 - 15.0) ----
    else:
        draw_logo(p, W / 2, H * 0.28, 840)
        text(p, "Descárgalo gratis", H * 0.45, 90, WHITE)
        bw, bh = 705, 144
        bx, by = (W - bw) / 2, H * 0.54
        p.setPen(Qt.NoPen)
        p.setBrush(GREEN)
        p.drawRoundedRect(QRectF(bx, by, bw, bh), 24, 24)
        text(p, "DESCARGAR", by + 32, 63, WHITE)
        text(p, "github.com/fcarvajalbrown/Keel", H * 0.66, 51, TEAL_DK)
        text(p, "código abierto · sin IA · sin suscripción", H * 0.71, 45, MUTED, False)

    # fade to black over the tail so the last frame == the first frame (black):
    # a seamless loop, which compounds Instagram replays / watch time.
    if t >= 14.0:
        p.setOpacity(max(0.0, min(1.0, (t - 14.0) / 0.8)))
        p.fillRect(0, 0, W, H, BLACK)
        p.setOpacity(1.0)

    p.end()

    ba = QByteArray()
    buf = QBuffer(ba)
    buf.open(QBuffer.ReadWrite)
    img.save(buf, "PNG")
    buf.close()
    return Image.open(io.BytesIO(bytes(ba))).convert("RGB")


def main():
    app = QGuiApplication(sys.argv)  # noqa: F841 - init Qt paint stack
    load_fonts()
    total = int(DUR * FPS)

    writer = iio.get_writer(MP4, fps=FPS, codec="libx264", quality=8,
                            macro_block_size=8, pixelformat="yuv420p")
    gif_frames = []
    for i in range(total):
        frame = render_frame(i, total)
        writer.append_data(np.asarray(frame))
        gif_frames.append(frame.resize(GIF_SIZE))
    writer.close()

    gif_frames[0].save(GIF, save_all=True, append_images=gif_frames[1:],
                       duration=int(1000 / FPS), loop=0, optimize=True, disposal=2)

    print(f"video saved: {MP4}  {W}x{H}  {total} frames  {DUR:.0f}s  "
          f"{os.path.getsize(MP4)/1_000_000:.1f} MB")
    print(f"gif saved:   {GIF}  {GIF_SIZE[0]}x{GIF_SIZE[1]}  "
          f"{os.path.getsize(GIF)/1_000_000:.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
