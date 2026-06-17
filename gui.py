# Keel — desktop GUI.
# Copyright (C) 2026 Felipe Carvajal Brown
#
# Part of the Keel GUI: licensed under the PolyForm Noncommercial License 1.0.0
# plus an additional free-use grant for individual musicians making their own
# music — see LICENSE-GUI.md. Business/redistribution use needs a commercial
# license (COMMERCIAL-LICENSE.md) or contact fcarvajalbrown@gmail.com.
# (The engine it imports — keel/recipes/mixer/mastering/meters — is AGPL-3.0.)
"""
gui.py  —  Keel's standalone desktop front-end (PySide6 / Qt).

A thin window over the SAME engine the CLI drives (`import keel`): the DSP is
never forked. Workflow:

  1. Drop (or open) a folder of finished stems.
  2. Keel auto-detects a label per file into an editable table; sharing a label
     groups files (balanced as one).
  3. Tweak per-label balance faders (relative LU), pick a loudness preset or set
     a custom target/ceiling, optionally a reference master, toggle bus glue.
     With "Live preview" on, a fader move re-renders automatically (debounced).
  4. One click renders mix + master in a background thread; the LUFS / true-peak
     meters (read via meters.py, the engine's own math) show where it landed.
     "Play master" streams the result and drives those meters live (short-term).
  5. Save/load named user presets and the whole project (its keel.json).

Run:  .venv\\Scripts\\python.exe gui.py   (install Qt first: setup.ps1 -Gui)
"""
import math
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

try:
    from PySide6.QtCore import QObject, Qt, QThread, QTimer, Signal
    from PySide6.QtGui import QFont
    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QGridLayout, QLabel, QPushButton, QSlider, QComboBox, QDoubleSpinBox,
        QCheckBox, QLineEdit, QFileDialog, QTableWidget, QTableWidgetItem,
        QPlainTextEdit, QInputDialog, QMessageBox, QGroupBox,
        QScrollArea, QHeaderView, QFrame,
    )
except ImportError as e:  # pragma: no cover - GUI is an optional extra
    raise SystemExit(
        "PySide6 is required for the GUI. Install it with:\n"
        "    .\\setup.ps1 -Gui        (or:  pip install PySide6)"
    ) from e

import gui_theme

try:
    from PySide6.QtMultimedia import QAudioFormat, QAudioSink, QMediaDevices
    _HAVE_AUDIO = True
except Exception:  # pragma: no cover - QtMultimedia absent / no audio backend
    _HAVE_AUDIO = False

import keel
import build
import userpresets

CUSTOM = "(custom)"
BAL_MIN, BAL_MAX = -30.0, 6.0   # fader range in LU (x10 internally for 0.1 steps)


class RenderWorker(QThread):
    """Mix + master off the UI thread so the window stays responsive."""
    done = Signal(dict)
    failed = Signal(str)
    progress = Signal(str)

    def __init__(self, stems_dir, out_dir, name, doc, glue, ref_path):
        super().__init__()
        self.stems_dir, self.out_dir, self.name = stems_dir, out_dir, name
        self.doc, self.glue, self.ref_path = doc, glue, ref_path

    def run(self):
        try:
            out = Path(self.out_dir)
            out.mkdir(parents=True, exist_ok=True)
            mix_wav = out / f"{self.name}_mix.wav"
            master_wav = out / f"{self.name}_master.wav"
            mix_ov = {"balance": self.doc.get("balance", {}),
                      "pan": self.doc.get("pan", {}),
                      "spread": self.doc.get("spread", {}),
                      "chain": self.doc.get("chain", {})}
            self.progress.emit("Mixing...")
            mrep = keel.mix(self.stems_dir, keel.mix_recipe(mix_ov), mix_wav,
                            mapping=self.doc.get("stems"), glue=self.glue)
            m_ov = dict(self.doc.get("master", {}))
            refs_dir = None
            if self.ref_path:
                p = Path(self.ref_path)
                refs_dir, m_ov["reference"] = p.parent, p.name
            else:
                m_ov["reference"] = None
            recipe = keel.master_recipe(m_ov)
            self.progress.emit("Mastering...")
            arep = keel.master(mix_wav, recipe, master_wav,
                               references_dir=refs_dir)
            self.done.emit({"mix": mrep, "master": arep,
                            "target": recipe.get("target_lufs"),
                            "mix_wav": str(mix_wav),
                            "master_wav": str(master_wav)})
        except Exception as e:  # surface any engine error in the UI
            self.failed.emit(f"{type(e).__name__}: {e}")


class PlaybackMeter(QObject):
    """Stream a rendered WAV to the audio device and meter it live.

    Pushes Int16 PCM to a QAudioSink in small chunks; on a timer it reads the
    sink's playback position and measures a trailing window with keel's own
    LUFS / true-peak math (the same meters.py the engine uses) so the meters
    move with the audio. Strictly display-only — nothing here touches the
    deterministic render path. Degrades to a no-op if QtMultimedia or an audio
    output device is unavailable (see `available`)."""
    levels = Signal(float, float)   # short-term LUFS, true-peak dBTP
    finished = Signal()

    WINDOW_S = 3.0        # trailing window for the short-term LUFS / TP readout
    METER_EVERY_MS = 150  # throttle the meter recompute (the push tick is faster)
    TICK_MS = 40

    def __init__(self, parent=None):
        super().__init__(parent)
        self.sink = None
        self.io = None
        self.audio = None
        self.rate = None
        self.pcm = b""
        self.cursor = 0
        self.frame_bytes = 4
        self.total_us = 0
        self._since_meter = 0
        self.timer = QTimer(self)
        self.timer.setInterval(self.TICK_MS)
        self.timer.timeout.connect(self._tick)

    def available(self):
        """True only if Qt multimedia loaded AND a default output device exists."""
        return _HAVE_AUDIO and not QMediaDevices.defaultAudioOutput().isNull()

    @property
    def playing(self):
        return self.sink is not None

    def play(self, wav_path):
        """Load `wav_path`, open a QAudioSink in push mode, and start streaming."""
        self.stop()
        audio, rate = sf.read(str(wav_path), dtype="float32", always_2d=True)
        ch = audio.shape[1]
        self.audio, self.rate = audio, rate
        self.frame_bytes = ch * 2  # Int16 -> 2 bytes/sample/channel
        self.pcm = (np.clip(audio, -1.0, 1.0) * 32767.0).astype("<i2").tobytes()
        self.cursor = 0
        self.total_us = int(audio.shape[0] / rate * 1_000_000)
        self._since_meter = 0

        fmt = QAudioFormat()
        fmt.setSampleRate(int(rate))
        fmt.setChannelCount(int(ch))
        fmt.setSampleFormat(QAudioFormat.SampleFormat.Int16)
        self.sink = QAudioSink(QMediaDevices.defaultAudioOutput(), fmt)
        self.io = self.sink.start()  # push-mode QIODevice
        self.timer.start()

    def _tick(self):
        if self.sink is None:
            return
        # feed the device as much frame-aligned data as it will currently take
        free = self.sink.bytesFree()
        free -= free % self.frame_bytes
        if free > 0 and self.cursor < len(self.pcm):
            end = min(self.cursor + free, len(self.pcm))
            written = self.io.write(self.pcm[self.cursor:end])
            if written > 0:
                self.cursor += written
        # update the meters off the actual playback position, throttled
        self._since_meter += self.TICK_MS
        if self._since_meter >= self.METER_EVERY_MS:
            self._since_meter = 0
            self._emit_levels()
        # done once everything pushed has actually played out
        if (self.cursor >= len(self.pcm)
                and self.sink.processedUSecs() >= self.total_us):
            self.stop()
            self.finished.emit()

    def _emit_levels(self):
        pos = int(self.sink.processedUSecs() / 1_000_000 * self.rate)
        lo = max(0, pos - int(self.WINDOW_S * self.rate))
        window = self.audio[lo:pos]
        if window.shape[0] < int(0.4 * self.rate):  # too short for a gated read
            return
        self.levels.emit(float(keel.integrated_lufs(window, self.rate)),
                         float(keel.true_peak_db(window, self.rate)))

    def stop(self):
        self.timer.stop()
        if self.sink is not None:
            try:
                self.sink.stop()
            except Exception:  # pragma: no cover - defensive teardown
                pass
        self.sink = None
        self.io = None


class KeelWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Keel — automix + automaster")
        self.resize(1080, 780)
        self.setMinimumSize(940, 640)
        self.setAcceptDrops(True)
        self.stems_dir = None
        self.doc = None
        self.out_dir = Path.cwd() / "out"
        self.worker = None
        self.balance_sliders = {}     # label -> (QSlider, QLabel)
        self.master_wav = None        # last rendered master, for playback
        self._render_levels = None    # (lufs, tp) of that master, to restore
        self.player = PlaybackMeter(self)
        self.player.levels.connect(self._on_live_levels)
        self.player.finished.connect(self._on_play_finished)
        # live re-render: a fader move (re)starts a single-shot debounce timer;
        # when it settles we re-render, coalescing moves made while one is running.
        self._pending_live = False
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(400)
        self._debounce.timeout.connect(self._fire_live_render)
        self._build_ui()
        self._refresh_presets()

    # ---------------------------------------------------------------- UI build
    def _build_ui(self):
        central = QWidget()
        central.setObjectName("root")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(20, 18, 20, 16)
        root.setSpacing(14)

        # header: hull mark + wordmark + tagline
        header = QHBoxLayout()
        header.setSpacing(12)
        header.addWidget(gui_theme.HullMark(40))
        title_col = QVBoxLayout()
        title_col.setSpacing(0)
        wordmark = QLabel("Keel")
        wordmark.setObjectName("wordmark")
        wf = gui_theme.font(22, QFont.Bold)
        wordmark.setFont(wf)
        wordmark.setStyleSheet(f"color: {gui_theme.COLORS['teal']};")
        tagline = QLabel("automatic mix + master")
        tagline.setObjectName("tagline")
        tagline.setFont(gui_theme.font(10.5))
        title_col.addWidget(wordmark)
        title_col.addWidget(tagline)
        header.addLayout(title_col)
        header.addStretch(1)
        root.addLayout(header)

        divider = QFrame()
        divider.setObjectName("divider")
        divider.setFixedHeight(1)
        root.addWidget(divider)

        # folder controls (drop strip)
        top = QHBoxLayout()
        self.open_btn = QPushButton("Open folder…")
        self.open_btn.clicked.connect(self._choose_folder)
        self.folder_lbl = QLabel("Drop a folder of stems here, or Open folder…")
        self.folder_lbl.setObjectName("folder")
        self.save_proj_btn = QPushButton("Save project")
        self.load_proj_btn = QPushButton("Load project")
        self.save_proj_btn.clicked.connect(self._save_project)
        self.load_proj_btn.clicked.connect(self._load_project)
        self.save_proj_btn.setEnabled(False)
        top.addWidget(self.open_btn)
        top.addWidget(self.folder_lbl, 1)
        top.addWidget(self.load_proj_btn)
        top.addWidget(self.save_proj_btn)
        root.addLayout(top)

        mid = QHBoxLayout()
        mid.setSpacing(14)
        root.addLayout(mid, 1)

        # left: stems table
        stems_box = QGroupBox("STEMS  ·  FILE -> LABEL")
        sb = QVBoxLayout(stems_box)
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["file", "label"])
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeToContents)
        sb.addWidget(self.table)
        self.relabel_btn = QPushButton("Apply label edits -> rebuild faders")
        self.relabel_btn.clicked.connect(self._rebuild_faders_from_table)
        self.relabel_btn.setEnabled(False)
        sb.addWidget(self.relabel_btn)
        mid.addWidget(stems_box, 3)

        # middle: balance faders
        bal_box = QGroupBox("BALANCE  ·  LU")
        bb = QVBoxLayout(bal_box)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.faders_holder = QWidget()
        self.faders_layout = QVBoxLayout(self.faders_holder)
        self.faders_layout.addStretch(1)
        scroll.setWidget(self.faders_holder)
        bb.addWidget(scroll)
        mid.addWidget(bal_box, 3)

        # right: master + meters + actions
        right = QVBoxLayout()
        mid.addLayout(right, 4)

        master_box = QGroupBox("MASTER")
        mg = QGridLayout(master_box)
        mg.setVerticalSpacing(10)
        mg.setHorizontalSpacing(8)
        mg.addWidget(QLabel("Preset"), 0, 0)
        self.preset_combo = QComboBox()
        self.preset_combo.currentTextChanged.connect(self._on_preset_changed)
        mg.addWidget(self.preset_combo, 0, 1)
        self.save_preset_btn = QPushButton("Save preset")
        self.del_preset_btn = QPushButton("Delete")
        self.save_preset_btn.clicked.connect(self._save_preset)
        self.del_preset_btn.clicked.connect(self._delete_preset)
        mg.addWidget(self.save_preset_btn, 0, 2)
        mg.addWidget(self.del_preset_btn, 0, 3)

        mg.addWidget(QLabel("Target LUFS"), 1, 0)
        self.target_spin = QDoubleSpinBox()
        self.target_spin.setRange(-30.0, 0.0)
        self.target_spin.setSingleStep(0.5)
        self.target_spin.setValue(keel.DEFAULT_MASTER["target_lufs"])
        self.target_spin.valueChanged.connect(self._on_master_edited)
        mg.addWidget(self.target_spin, 1, 1)
        mg.addWidget(QLabel("True-peak dBTP"), 1, 2)
        self.tp_spin = QDoubleSpinBox()
        self.tp_spin.setRange(-6.0, 0.0)
        self.tp_spin.setSingleStep(0.1)
        self.tp_spin.setValue(keel.DEFAULT_MASTER["tp_ceiling_db"])
        self.tp_spin.valueChanged.connect(self._on_master_edited)
        mg.addWidget(self.tp_spin, 1, 3)

        self.glue_chk = QCheckBox("Bus glue (gentle)")
        mg.addWidget(self.glue_chk, 2, 0, 1, 2)

        ref_lbl = QLabel("Reference")
        ref_tip = ("Optional. Leave blank to use Keel's default internal master "
                   "(the current behavior). Pick a mastered WAV/FLAC and Keel "
                   "matches its tone + loudness via Matchering instead — affects "
                   "only this render, nothing is forced.")
        ref_lbl.setToolTip(ref_tip)
        mg.addWidget(ref_lbl, 3, 0)
        self.ref_edit = QLineEdit()
        self.ref_edit.setPlaceholderText("optional — blank uses Keel's default master")
        self.ref_edit.setToolTip(ref_tip)
        ref_btn = QPushButton("Browse…")
        ref_btn.clicked.connect(self._choose_reference)
        mg.addWidget(self.ref_edit, 3, 1, 1, 2)
        mg.addWidget(ref_btn, 3, 3)
        right.addWidget(master_box)

        self.render_btn = QPushButton("Render mix + master")
        self.render_btn.setObjectName("primary")
        self.render_btn.setMinimumHeight(46)
        self.render_btn.setEnabled(False)
        self.render_btn.clicked.connect(self._render)
        right.addWidget(self.render_btn)

        self.live_chk = QCheckBox("Live preview (re-render on fader move)")
        self.live_chk.setToolTip(
            "Re-render mix + master a moment after a fader settles, so the "
            "meters track the new balance without clicking Render. Balance "
            "only — never tone (Keel's locked scope).")
        right.addWidget(self.live_chk)

        meters_box = QGroupBox("METERS")
        meters = QVBoxLayout(meters_box)
        meters.setSpacing(10)
        self.lufs_meter = gui_theme.Meter(
            "INTEGRATED LOUDNESS", "LUFS", -30.0, 0.0,
            target=self.target_spin.value())
        self.tp_meter = gui_theme.Meter(
            "TRUE PEAK", "dBTP", -12.0, 0.0,
            danger_above=self.tp_spin.value())
        meters.addWidget(self.lufs_meter)
        meters.addWidget(self.tp_meter)
        self.play_btn = QPushButton("Play master")
        self.play_btn.setToolTip(
            "Play the rendered master and drive the meters live (short-term, "
            "trailing 3 s). Display-only — does not change the render.")
        self.play_btn.setEnabled(False)
        self.play_btn.clicked.connect(self._toggle_play)
        meters.addWidget(self.play_btn)
        right.addWidget(meters_box)
        right.addStretch(1)

        self.log = QPlainTextEdit()
        self.log.setObjectName("log")
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(96)
        self.log.setFont(gui_theme.font(10))
        root.addWidget(self.log)

    # ---------------------------------------------------------------- drag/drop
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            p = Path(url.toLocalFile())
            if p.is_dir():
                self._load_folder(p)
                break

    # ---------------------------------------------------------------- helpers
    def _say(self, msg):
        self.log.appendPlainText(msg)

    def _choose_folder(self):
        d = QFileDialog.getExistingDirectory(self, "Choose a stems folder")
        if d:
            self._load_folder(Path(d))

    def _choose_reference(self):
        f, _ = QFileDialog.getOpenFileName(
            self, "Choose a reference master", "",
            "Audio (*.wav *.flac);;All files (*)")
        if f:
            self.ref_edit.setText(f)

    def _load_folder(self, folder):
        folder = Path(folder)
        mpath = folder / build.MAPPING_NAME
        try:
            if mpath.exists():
                self.doc = build.load_mapping_doc(mpath)
                self._say(f"Loaded existing mapping {mpath}")
            else:
                self.doc = build.build_mapping_doc(folder)
                self._say(f"Auto-detected labels for {folder.name}")
        except Exception as e:
            QMessageBox.critical(self, "Keel", f"Could not read folder:\n{e}")
            return
        if not self.doc.get("stems"):
            QMessageBox.warning(self, "Keel",
                                "No .wav/.flac stems found in that folder.")
            return
        self.stems_dir = folder
        self.out_dir = folder.parent / "out"
        self.folder_lbl.setText(f"{folder}    ->    out: {self.out_dir}")
        self.folder_lbl.setStyleSheet("")
        self._populate_from_doc()
        self.render_btn.setEnabled(True)
        self.save_proj_btn.setEnabled(True)
        self.relabel_btn.setEnabled(True)

    def _populate_from_doc(self):
        self._stop_playback()
        self._set_meters(None, None)
        stems = self.doc.get("stems", {})
        self.table.setRowCount(0)
        for fn, label in stems.items():
            r = self.table.rowCount()
            self.table.insertRow(r)
            item_f = QTableWidgetItem(fn)
            item_f.setFlags(item_f.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(r, 0, item_f)
            self.table.setItem(r, 1, QTableWidgetItem(label))
        self._rebuild_faders(self.doc.get("balance", {}),
                             labels=list(dict.fromkeys(stems.values())))
        m = self.doc.get("master", {})
        self.target_spin.setValue(float(m.get("target_lufs",
                                  keel.DEFAULT_MASTER["target_lufs"])))
        self.tp_spin.setValue(float(m.get("tp_ceiling_db",
                              keel.DEFAULT_MASTER["tp_ceiling_db"])))
        self.glue_chk.setChecked(bool(self.doc.get("glue", False)))
        self.ref_edit.setText(m.get("reference") or "")
        self._sync_preset_combo()

    def _clear_faders(self):
        while self.faders_layout.count():
            item = self.faders_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self.balance_sliders = {}

    def _rebuild_faders(self, balance, labels):
        self._clear_faders()
        # union of labels present + any extra in the balance dict, ordered
        seen = list(dict.fromkeys(list(labels) + list(balance.keys())))
        for label in seen:
            row = QWidget()
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 0, 0, 0)
            name = QLabel(label)
            name.setMinimumWidth(80)
            slider = QSlider(Qt.Horizontal)
            slider.setRange(int(BAL_MIN * 10), int(BAL_MAX * 10))
            val = float(balance.get(label, 0.0))
            slider.setValue(int(round(val * 10)))
            vlbl = QLabel(f"{val:+.1f}")
            vlbl.setMinimumWidth(44)
            slider.valueChanged.connect(
                lambda v, lb=vlbl: lb.setText(f"{v / 10:+.1f}"))
            slider.valueChanged.connect(self._on_fader_moved)
            rl.addWidget(name)
            rl.addWidget(slider, 1)
            rl.addWidget(vlbl)
            self.faders_layout.addWidget(row)
            self.balance_sliders[label] = (slider, vlbl)
        self.faders_layout.addStretch(1)

    def _rebuild_faders_from_table(self):
        # read edited labels out of the table, keep existing fader values
        stems, labels = {}, []
        cur = self._collect_balance()
        for r in range(self.table.rowCount()):
            fn = self.table.item(r, 0).text()
            lb = (self.table.item(r, 1).text() or build.mixer.OTHER_LABEL).strip()
            stems[fn] = lb
            labels.append(lb)
        self.doc["stems"] = stems
        self._rebuild_faders(cur, labels=list(dict.fromkeys(labels)))
        self._say("Rebuilt faders from edited labels.")

    def _collect_balance(self):
        return {lb: s.value() / 10.0 for lb, (s, _) in self.balance_sliders.items()}

    def _collect_doc(self):
        """Read the whole UI back into a keel.json-shaped doc."""
        stems = {}
        for r in range(self.table.rowCount()):
            fn = self.table.item(r, 0).text()
            lb = (self.table.item(r, 1).text() or build.mixer.OTHER_LABEL).strip()
            stems[fn] = lb
        doc = dict(self.doc or {})
        doc["stems"] = stems
        doc["balance"] = self._collect_balance()
        doc.setdefault("pan", {})
        doc.setdefault("spread", {})
        doc["glue"] = self.glue_chk.isChecked()
        ref = self.ref_edit.text().strip()
        doc["master"] = {
            "target_lufs": self.target_spin.value(),
            "tp_ceiling_db": self.tp_spin.value(),
            "reference": ref or None,
        }
        return doc

    # ---------------------------------------------------------------- presets
    def _refresh_presets(self):
        self.preset_combo.blockSignals(True)
        self.preset_combo.clear()
        self.preset_combo.addItem(CUSTOM)
        for name in userpresets.all_presets():
            self.preset_combo.addItem(name)
        self.preset_combo.blockSignals(False)

    def _sync_preset_combo(self):
        """Select the preset whose values match the current spins, else custom."""
        t, c = self.target_spin.value(), self.tp_spin.value()
        for name, m in userpresets.all_presets().items():
            if abs(m["target_lufs"] - t) < 1e-6 and abs(m["tp_ceiling_db"] - c) < 1e-6:
                self.preset_combo.setCurrentText(name)
                return
        self.preset_combo.setCurrentText(CUSTOM)

    def _on_preset_changed(self, name):
        if name and name != CUSTOM:
            m = userpresets.all_presets().get(name)
            if m:
                for spin, key in ((self.target_spin, "target_lufs"),
                                  (self.tp_spin, "tp_ceiling_db")):
                    spin.blockSignals(True)
                    spin.setValue(float(m[key]))
                    spin.blockSignals(False)

    def _on_master_edited(self, _=None):
        self._sync_preset_combo()
        # keep the meter ticks aligned with the chosen target / ceiling
        self.lufs_meter.target = self.target_spin.value()
        self.tp_meter.danger_above = self.tp_spin.value()
        self.lufs_meter.update()
        self.tp_meter.update()

    def _save_preset(self):
        name, ok = QInputDialog.getText(self, "Save preset", "Preset name:")
        if not ok or not name.strip():
            return
        try:
            userpresets.save_user_preset(
                name, {"target_lufs": self.target_spin.value(),
                       "tp_ceiling_db": self.tp_spin.value()})
        except ValueError as e:
            QMessageBox.warning(self, "Keel", str(e))
            return
        self._refresh_presets()
        self.preset_combo.setCurrentText(name.strip())
        self._say(f"Saved preset '{name.strip()}'.")

    def _delete_preset(self):
        name = self.preset_combo.currentText()
        if name in keel.PRESETS or name == CUSTOM:
            QMessageBox.information(self, "Keel",
                                    "Pick a user preset to delete "
                                    "(built-ins can't be removed).")
            return
        userpresets.delete_user_preset(name)
        self._refresh_presets()
        self._say(f"Deleted preset '{name}'.")

    # ---------------------------------------------------------------- project
    def _save_project(self):
        if not self.stems_dir:
            return
        doc = self._collect_doc()
        default = str(self.stems_dir / build.MAPPING_NAME)
        f, _ = QFileDialog.getSaveFileName(self, "Save project (keel.json)",
                                           default, "Keel mapping (*.json)")
        if f:
            build.write_mapping_doc(f, doc)
            self.doc = doc
            self._say(f"Saved project -> {f}")

    def _load_project(self):
        f, _ = QFileDialog.getOpenFileName(self, "Load project (keel.json)",
                                           "", "Keel mapping (*.json)")
        if not f:
            return
        try:
            self.doc = build.load_mapping_doc(f)
        except Exception as e:
            QMessageBox.critical(self, "Keel", f"Could not load:\n{e}")
            return
        self.stems_dir = Path(f).parent
        self.out_dir = self.stems_dir.parent / "out"
        self.folder_lbl.setText(f"{self.stems_dir}    ->    out: {self.out_dir}")
        self.folder_lbl.setStyleSheet("")
        self._populate_from_doc()
        self.render_btn.setEnabled(True)
        self.save_proj_btn.setEnabled(True)
        self.relabel_btn.setEnabled(True)
        self._say(f"Loaded project {f}")

    # ---------------------------------------------------------------- render
    def _on_fader_moved(self, _=None):
        """A balance fader changed: if live preview is on, (re)arm the debounce."""
        if self.live_chk.isChecked() and self.stems_dir:
            self._debounce.start()

    def _fire_live_render(self):
        """Debounce settled — re-render now, or queue one if a render is running."""
        if not self.live_chk.isChecked() or not self.stems_dir:
            return
        if self.worker is not None:
            self._pending_live = True   # coalesce: re-render once this one finishes
            return
        self._start_render(live=True)

    def _render(self):
        self._start_render(live=False)

    def _start_render(self, live=False):
        if not self.stems_dir or self.worker:
            return
        doc = self._collect_doc()
        self.doc = doc
        self.render_btn.setEnabled(False)
        self.render_btn.setText("Re-rendering…" if live else "Rendering…")
        self.worker = RenderWorker(
            self.stems_dir, self.out_dir, self.stems_dir.name, doc,
            glue=doc["glue"], ref_path=doc["master"]["reference"])
        self.worker.progress.connect(self._say)
        self.worker.done.connect(self._render_done)
        self.worker.failed.connect(self._render_failed)
        self.worker.finished.connect(self._render_cleanup)
        self.worker.start()

    def _render_done(self, res):
        mix, mst = res["mix"], res["master"]
        self._say(f"Mix    -> {res['mix_wav']}  "
                  f"({mix['seconds']}s, peak {mix['peak_dbfs']} dBFS)")
        self._say(f"Master -> {res['master_wav']}  "
                  f"[{mst['path']}]  {mst['lufs']} LUFS  "
                  f"{mst['true_peak_db']} dBTP")
        self._set_meters(mst.get("lufs"), mst.get("true_peak_db"))
        self.master_wav = res["master_wav"]
        self._render_levels = (mst.get("lufs"), mst.get("true_peak_db"))
        if not self.player.playing:
            self.play_btn.setEnabled(True)

    def _render_failed(self, msg):
        self._say(f"ERROR: {msg}")
        QMessageBox.critical(self, "Keel — render failed", msg)

    def _render_cleanup(self):
        self.worker = None
        self.render_btn.setText("Render mix + master")
        self.render_btn.setEnabled(True)
        if self._pending_live and self.live_chk.isChecked():
            self._pending_live = False
            self._start_render(live=True)

    def _set_meters(self, lufs, tp):
        self.lufs_meter.set_value(lufs)
        self.tp_meter.set_value(tp)

    # ---------------------------------------------------------------- playback
    def _toggle_play(self):
        if self.player.playing:
            self.player.stop()
            self._on_play_finished()
            return
        if not self.master_wav or not Path(self.master_wav).exists():
            return
        if not self.player.available():
            QMessageBox.information(self, "Keel",
                                    "No audio output device is available.")
            return
        try:
            self.player.play(self.master_wav)
        except Exception as e:
            QMessageBox.warning(self, "Keel", f"Playback failed:\n{e}")
            return
        self.play_btn.setText("Stop")
        self._say(f"Playing {Path(self.master_wav).name} (live meters)")

    def _on_live_levels(self, lufs, tp):
        # the trailing-window short-term read, pushed onto the same meters
        self._set_meters(lufs if math.isfinite(lufs) else None,
                         tp if math.isfinite(tp) else None)

    def _on_play_finished(self):
        self.play_btn.setText("Play master")
        if self._render_levels is not None:  # restore the integrated readings
            self._set_meters(*self._render_levels)

    def _stop_playback(self):
        """Tear playback down and reset its UI (on a new folder/project load)."""
        self.player.stop()
        self.play_btn.setText("Play master")
        self.play_btn.setEnabled(False)
        self.master_wav = None
        self._render_levels = None

    def closeEvent(self, event):
        self.player.stop()  # don't leave an audio stream running after close
        super().closeEvent(event)


def _apply_theme(app):
    """Load the bundled font and paint the app in Keel's dark teal theme."""
    family = gui_theme.load_fonts()
    base = gui_theme.font(10)
    app.setFont(base)
    gui_theme.apply_palette(app)
    app.setStyleSheet(gui_theme.build_stylesheet(family))
    return family


def _selftest():
    """Headless smoke test of the *packaged* app: build the window offscreen and
    confirm the engine is reachable, then exit. Run as `Keel.exe --selftest` in
    CI (and locally) to prove a frozen build actually imports Qt + the engine."""
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication(sys.argv)
    family = _apply_theme(app)
    KeelWindow()
    print(f"Keel selftest OK — engine {keel.__version__}, "
          f"font '{family}', presets {sorted(keel.PRESETS)}")
    app.quit()
    return 0


def main():
    if "--selftest" in sys.argv[1:]:
        return _selftest()
    app = QApplication(sys.argv)
    _apply_theme(app)
    win = KeelWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
