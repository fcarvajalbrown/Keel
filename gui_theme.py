# Keel — desktop GUI theme.
# Copyright (C) 2026 Felipe Carvajal Brown
#
# Part of the Keel GUI: licensed under the PolyForm Noncommercial License 1.0.0
# plus an additional free-use grant for individual musicians making their own
# music — see LICENSE-NONCOMMERCIAL.md. Business/redistribution use needs a commercial
# license (COMMERCIAL-LICENSE.md) or contact fcarvajalbrown@gmail.com.
"""
gui_theme.py  —  the look of Keel's desktop app.

A dark, minimal, "mastering-room" theme built around Keel's own teal brand
(#27D2C0 -> #0C8C81, the logo gradient). Holds, in one place:

  * COLORS         — the palette (one source of truth, used by QSS + painters).
  * load_fonts()   — registers the bundled Space Grotesk family (SIL OFL,
                     assets/fonts/), falling back to a system sans if missing.
  * build_stylesheet() — the global Qt stylesheet string.
  * HullMark       — the Keel hull+waveform logo, hand-painted so it stays crisp
                     at any DPI and always matches the palette.
  * Meter          — a custom LUFS / true-peak meter (gradient bar + target /
                     ceiling ticks + a big numeric readout) replacing QProgressBar.

Nothing here touches the engine or the render path — it is purely presentation.
"""
import sys
from pathlib import Path
from string import Template

from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import (
    QBrush, QColor, QFont, QFontDatabase, QLinearGradient, QPainter,
    QPainterPath, QPalette, QPen,
)
from PySide6.QtWidgets import QWidget, QSizePolicy


# --------------------------------------------------------------------- palette
# Dark base with a slight cool tint; teal accent lifted straight from the logo.
COLORS = {
    "bg":        "#0E1314",   # window background (near-black, faint teal tint)
    "surface":   "#151B1D",   # cards / panels
    "surface2":  "#1C2427",   # inputs / elevated controls
    "line":      "#283133",   # hairline borders / track grooves
    "text":      "#E7EEED",   # primary text (cool off-white)
    "muted":     "#8A9A9C",   # secondary text / section labels
    "faint":     "#5C6B6E",   # tertiary / disabled / placeholders
    "teal":      "#27D2C0",   # accent (logo top stop)
    "teal_hi":   "#46E2D2",   # accent hover
    "teal_deep": "#0C8C81",   # accent deep (logo bottom stop)
    "ink":       "#06201E",   # text on a teal fill
    "amber":     "#E8B14C",   # caution (approaching a ceiling)
    "red":       "#F0594F",   # over a ceiling / danger
}

# Set by load_fonts(); read by the custom painters. Safe default until then.
DISPLAY_FAMILY = "Sans Serif"


# ----------------------------------------------------------------- resources
def resource_path(*parts):
    """Resolve a bundled asset both in-repo and inside a PyInstaller onefile."""
    base = getattr(sys, "_MEIPASS", None)
    base = Path(base) if base else Path(__file__).resolve().parent
    return base.joinpath(*parts)


def load_fonts():
    """Register the bundled Space Grotesk weights; return the family name.

    Falls back to a sensible system sans if the TTFs are missing (e.g. a
    stripped build) so the app still themes cleanly."""
    global DISPLAY_FAMILY
    fonts_dir = resource_path("assets", "fonts")
    family = None
    for ttf in ("SpaceGrotesk-Regular.ttf", "SpaceGrotesk-Medium.ttf",
                "SpaceGrotesk-Bold.ttf"):
        fid = QFontDatabase.addApplicationFont(str(fonts_dir / ttf))
        if fid != -1 and family is None:
            fams = QFontDatabase.applicationFontFamilies(fid)
            if fams:
                family = fams[0]
    if not family:
        family = "Segoe UI" if sys.platform.startswith("win") else "Sans Serif"
    DISPLAY_FAMILY = family
    return family


def font(size, weight=QFont.Normal):
    """A QFont in the display family at a given point size / weight."""
    f = QFont(DISPLAY_FAMILY)
    f.setPointSizeF(size)
    f.setWeight(weight)
    return f


# ---------------------------------------------------------------- stylesheet
_QSS = Template("""
* {
    font-family: "$font";
    font-size: 13px;
    color: $text;
    outline: none;
}
QMainWindow, QWidget#root { background: $bg; }
QToolTip {
    background: $surface2; color: $text;
    border: 1px solid $line; border-radius: 6px; padding: 6px 8px;
}

/* ---- cards (QGroupBox styled as panels) ---- */
QGroupBox {
    background: $surface;
    border: 1px solid $line;
    border-radius: 12px;
    margin-top: 16px;
    padding: 16px 14px 14px 14px;
    font-size: 11px;
    font-weight: 600;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 14px; top: 0px;
    padding: 2px 6px;
    color: $muted;
    background: transparent;
}

/* ---- buttons ---- */
QPushButton {
    background: $surface2;
    border: 1px solid $line;
    border-radius: 8px;
    padding: 7px 14px;
    color: $text;
}
QPushButton:hover { border-color: $teal_deep; color: $teal_hi; }
QPushButton:pressed { background: #11171a; }
QPushButton:disabled { color: $faint; background: $surface; border-color: $surface2; }

QPushButton#primary {
    background: $teal;
    color: $ink;
    border: none;
    border-radius: 10px;
    font-size: 15px;
    font-weight: 700;
    padding: 10px 16px;
}
QPushButton#primary:hover { background: $teal_hi; }
QPushButton#primary:pressed { background: $teal_deep; }
QPushButton#primary:disabled { background: #1d3b39; color: #527a76; }

/* ---- inputs ---- */
QLineEdit, QComboBox, QAbstractSpinBox {
    background: $surface2;
    border: 1px solid $line;
    border-radius: 8px;
    padding: 6px 8px;
    color: $text;
    selection-background-color: $teal_deep;
    selection-color: $text;
}
QLineEdit:focus, QComboBox:focus, QAbstractSpinBox:focus { border-color: $teal; }
QLineEdit::placeholder { color: $faint; }
QComboBox::drop-down { border: none; width: 22px; }
QComboBox QAbstractItemView {
    background: $surface2;
    border: 1px solid $line;
    border-radius: 8px;
    selection-background-color: $teal_deep;
    selection-color: $text;
    padding: 4px;
}
QAbstractSpinBox::up-button, QAbstractSpinBox::down-button {
    width: 16px; border: none; background: transparent;
}

/* ---- checkbox ---- */
QCheckBox { spacing: 8px; color: $text; background: transparent; }
QCheckBox::indicator {
    width: 18px; height: 18px;
    border: 1px solid $line; border-radius: 5px; background: $surface2;
}
QCheckBox::indicator:hover { border-color: $teal_deep; }
QCheckBox::indicator:checked { background: $teal; border-color: $teal; }

/* ---- sliders (balance faders) ---- */
QSlider::groove:horizontal { height: 4px; background: $line; border-radius: 2px; }
QSlider::sub-page:horizontal { background: $teal_deep; border-radius: 2px; }
QSlider::add-page:horizontal { background: $line; border-radius: 2px; }
QSlider::handle:horizontal {
    background: $teal; width: 14px; height: 14px;
    margin: -6px 0; border-radius: 7px;
}
QSlider::handle:horizontal:hover { background: $teal_hi; }

/* ---- table ---- */
QTableWidget, QTableView {
    background: $surface;
    alternate-background-color: #12181a;
    border: none;
    gridline-color: transparent;
    selection-background-color: $teal_deep;
    selection-color: $text;
}
QTableWidget::item { padding: 4px 6px; border: none; }
QTableWidget::item:selected { background: $teal_deep; }
QHeaderView::section {
    background: $surface;
    color: $muted;
    border: none;
    border-bottom: 1px solid $line;
    padding: 6px;
    font-size: 11px;
    font-weight: 600;
}
QTableCornerButton::section { background: $surface; border: none; }

/* ---- scroll ---- */
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 0; }
QScrollBar::handle:vertical { background: $line; border-radius: 5px; min-height: 24px; }
QScrollBar::handle:vertical:hover { background: $teal_deep; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 0; }
QScrollBar::handle:horizontal { background: $line; border-radius: 5px; min-width: 24px; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }

/* ---- log console ---- */
QPlainTextEdit#log {
    background: #0A0E0F;
    border: 1px solid $line;
    border-radius: 10px;
    color: $muted;
    padding: 8px;
}

/* ---- header / section labels (font set in code) ---- */
QLabel#tagline { color: $muted; }
QLabel#folder  { color: $muted; }
QLabel#hint    { color: $faint; }
QFrame#divider { background: $line; max-height: 1px; border: none; }

QProgressBar {
    background: $surface2; border: 1px solid $line; border-radius: 6px;
    text-align: center; color: $text;
}
QProgressBar::chunk { background: $teal_deep; border-radius: 5px; }
""")


def build_stylesheet(family=None):
    return _QSS.substitute(font=family or DISPLAY_FAMILY, **COLORS)


def apply_palette(app):
    """Set a dark base palette so any widget the stylesheet doesn't reach (plain
    QWidget viewports, popups) draws dark instead of the OS light default."""
    c = COLORS
    pal = app.palette()
    pal.setColor(QPalette.Window, QColor(c["bg"]))
    pal.setColor(QPalette.WindowText, QColor(c["text"]))
    pal.setColor(QPalette.Base, QColor(c["surface"]))
    pal.setColor(QPalette.AlternateBase, QColor("#12181a"))
    pal.setColor(QPalette.Text, QColor(c["text"]))
    pal.setColor(QPalette.Button, QColor(c["surface2"]))
    pal.setColor(QPalette.ButtonText, QColor(c["text"]))
    pal.setColor(QPalette.PlaceholderText, QColor(c["faint"]))
    pal.setColor(QPalette.Highlight, QColor(c["teal_deep"]))
    pal.setColor(QPalette.HighlightedText, QColor(c["text"]))
    pal.setColor(QPalette.ToolTipBase, QColor(c["surface2"]))
    pal.setColor(QPalette.ToolTipText, QColor(c["text"]))
    pal.setColor(QPalette.Disabled, QPalette.Text, QColor(c["faint"]))
    pal.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(c["faint"]))
    app.setPalette(pal)


# ------------------------------------------------------------------ widgets
# Hull mark geometry, lifted verbatim from assets/keel-logo.svg so the painted
# mark and the brand logo are the same drawing. (src coords; scaled at paint.)
_HULL = [(8, 18), (28, 96), (92, 96), (112, 18)]      # outline + quad control
_HULL_Q = (60, 120)                                   # quadratic control point
_BARS = [                                              # waveform bars (x,y,w,h)
    (56.5, 30, 7, 80), (45.5, 40, 7, 70), (67.5, 40, 7, 70),
    (34.5, 52, 7, 58), (78.5, 52, 7, 58),
    (23.5, 66, 7, 44), (89.5, 66, 7, 44),
]
_SRC = (8, 18, 104, 102)   # bounding box of the mark in source coords


class HullMark(QWidget):
    """Keel's hull + balanced-waveform logo, painted in the teal gradient."""

    def __init__(self, size=40, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        mx, my, mw, mh = _SRC
        margin = 2
        avail_w, avail_h = self.width() - 2 * margin, self.height() - 2 * margin
        s = min(avail_w / mw, avail_h / mh)
        p.translate(margin + (avail_w - mw * s) / 2,
                    margin + (avail_h - mh * s) / 2)
        p.scale(s, s)
        p.translate(-mx, -my)

        grad = QLinearGradient(0, my, 0, my + mh)
        grad.setColorAt(0.0, QColor(COLORS["teal"]))
        grad.setColorAt(1.0, QColor(COLORS["teal_deep"]))

        # closed hull region, used to clip the waveform bars
        clip = QPainterPath()
        clip.moveTo(*_HULL[0])
        clip.lineTo(*_HULL[1])
        clip.quadTo(_HULL_Q[0], _HULL_Q[1], _HULL[2][0], _HULL[2][1])
        clip.lineTo(*_HULL[3])
        clip.closeSubpath()

        p.save()
        p.setClipPath(clip)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(grad))
        for x, y, w, h in _BARS:
            p.drawRoundedRect(QRectF(x, y, w, h), 3.5, 3.5)
        p.restore()

        # open-top hull outline
        outline = QPainterPath()
        outline.moveTo(*_HULL[0])
        outline.lineTo(*_HULL[1])
        outline.quadTo(_HULL_Q[0], _HULL_Q[1], _HULL[2][0], _HULL[2][1])
        outline.lineTo(*_HULL[3])
        pen = QPen(QBrush(grad), 9)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawPath(outline)


class Meter(QWidget):
    """A horizontal LUFS / true-peak meter: title + big readout + gradient bar
    with target / ceiling ticks. Display-only; fed by KeelWindow._set_meters.

    `danger_above` (e.g. the true-peak ceiling) flips the fill + readout to a
    warm->red gradient when the reading exceeds it."""

    def __init__(self, title, unit, vmin, vmax,
                 target=None, danger_above=None, parent=None):
        super().__init__(parent)
        self.title = title
        self.unit = unit
        self.vmin, self.vmax = float(vmin), float(vmax)
        self.target = target
        self.danger_above = danger_above
        self.value = None
        self.setFixedHeight(58)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set_value(self, v):
        self.value = None if v is None else float(v)
        self.update()

    def _frac(self, v):
        return max(0.0, min(1.0, (v - self.vmin) / (self.vmax - self.vmin)))

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        over = (self.value is not None and self.danger_above is not None
                and self.value > self.danger_above)

        # title (top-left)
        p.setPen(QColor(COLORS["muted"]))
        p.setFont(font(8.5, QFont.Medium))
        p.drawText(QRectF(0, 0, w, 18), Qt.AlignLeft | Qt.AlignVCenter,
                   self.title)

        # numeric readout (top-right)
        if self.value is None:
            readout, color = "--", QColor(COLORS["faint"])
        else:
            readout = f"{self.value:.1f} {self.unit}"
            color = QColor(COLORS["red"]) if over else QColor(COLORS["teal"])
        p.setPen(color)
        p.setFont(font(16, QFont.Bold))
        p.drawText(QRectF(0, -2, w, 24), Qt.AlignRight | Qt.AlignVCenter,
                   readout)

        # track
        ty, th = h - 14, 8
        track = QRectF(0, ty, w, th)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(COLORS["surface2"]))
        p.drawRoundedRect(track, 4, 4)

        # fill
        if self.value is not None:
            fw = w * self._frac(self.value)
            if fw > 2:
                fill = QRectF(0, ty, fw, th)
                grad = QLinearGradient(0, 0, max(fw, w), 0)
                if over:
                    grad.setColorAt(0.0, QColor(COLORS["amber"]))
                    grad.setColorAt(1.0, QColor(COLORS["red"]))
                else:
                    grad.setColorAt(0.0, QColor(COLORS["teal_deep"]))
                    grad.setColorAt(1.0, QColor(COLORS["teal"]))
                p.setBrush(QBrush(grad))
                p.drawRoundedRect(fill, 4, 4)

        # ticks: target (muted) and ceiling/danger (red)
        for val, col in ((self.target, QColor(COLORS["text"])),
                         (self.danger_above, QColor(COLORS["red"]))):
            if val is None:
                continue
            tx = w * self._frac(val)
            p.setPen(QPen(col, 2))
            p.drawLine(QPointF(tx, ty - 3), QPointF(tx, ty + th + 3))
