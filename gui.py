# Keel — automix + automaster engine.
# Copyright (C) 2026 Felipe Carvajal Brown
#
# Licensed under the GNU Affero General Public License v3.0 (see LICENSE).
# A commercial license is available — see COMMERCIAL-LICENSE.md
# or contact fcarvajalbrown@gmail.com.
"""
gui.py  —  Keel's standalone desktop front-end (PySide6 / Qt).

A thin window over the SAME engine the CLI drives (`import keel`): the DSP is
never forked. Workflow:

  1. Drop (or open) a folder of finished stems.
  2. Keel auto-detects a label per file into an editable table; sharing a label
     groups files (balanced as one).
  3. Tweak per-label balance faders (relative LU), pick a loudness preset or set
     a custom target/ceiling, optionally a reference master, toggle bus glue.
  4. One click renders mix + master in a background thread; the LUFS / true-peak
     meters (read via meters.py, the engine's own math) show where it landed.
  5. Save/load named user presets and the whole project (its keel.json).

Run:  .venv\\Scripts\\python.exe gui.py   (install Qt first: setup.ps1 -Gui)
"""
import sys
from pathlib import Path

try:
    from PySide6.QtCore import Qt, QThread, QTimer, Signal
    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QGridLayout, QLabel, QPushButton, QSlider, QComboBox, QDoubleSpinBox,
        QCheckBox, QLineEdit, QFileDialog, QTableWidget, QTableWidgetItem,
        QProgressBar, QPlainTextEdit, QInputDialog, QMessageBox, QGroupBox,
        QScrollArea, QHeaderView,
    )
except ImportError as e:  # pragma: no cover - GUI is an optional extra
    raise SystemExit(
        "PySide6 is required for the GUI. Install it with:\n"
        "    .\\setup.ps1 -Gui        (or:  pip install PySide6)"
    ) from e

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


class KeelWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Keel — automix + automaster")
        self.resize(960, 640)
        self.setAcceptDrops(True)
        self.stems_dir = None
        self.doc = None
        self.out_dir = Path.cwd() / "out"
        self.worker = None
        self.balance_sliders = {}     # label -> (QSlider, QLabel)
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
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        # top: folder controls
        top = QHBoxLayout()
        self.open_btn = QPushButton("Open folder…")
        self.open_btn.clicked.connect(self._choose_folder)
        self.folder_lbl = QLabel("Drop a folder of stems here, or Open folder…")
        self.folder_lbl.setStyleSheet("color: #888;")
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
        root.addLayout(mid, 1)

        # left: stems table
        stems_box = QGroupBox("Stems  (file -> label)")
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
        bal_box = QGroupBox("Balance (LU)")
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

        master_box = QGroupBox("Master")
        mg = QGridLayout(master_box)
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

        mg.addWidget(QLabel("Reference"), 3, 0)
        self.ref_edit = QLineEdit()
        self.ref_edit.setPlaceholderText("optional WAV/FLAC master to match…")
        ref_btn = QPushButton("Browse…")
        ref_btn.clicked.connect(self._choose_reference)
        mg.addWidget(self.ref_edit, 3, 1, 1, 2)
        mg.addWidget(ref_btn, 3, 3)
        right.addWidget(master_box)

        self.render_btn = QPushButton("Render mix + master")
        self.render_btn.setMinimumHeight(40)
        self.render_btn.setEnabled(False)
        self.render_btn.clicked.connect(self._render)
        right.addWidget(self.render_btn)

        self.live_chk = QCheckBox("Live preview (re-render on fader move)")
        self.live_chk.setToolTip(
            "Re-render mix + master a moment after a fader settles, so the "
            "meters track the new balance without clicking Render. Balance "
            "only — never tone (Keel's locked scope).")
        right.addWidget(self.live_chk)

        meters_box = QGroupBox("Master meters")
        meters = QGridLayout(meters_box)
        meters.addWidget(QLabel("LUFS"), 0, 0)
        self.lufs_bar = QProgressBar()
        self.lufs_bar.setRange(0, 100)
        self.lufs_val = QLabel("–")
        meters.addWidget(self.lufs_bar, 0, 1)
        meters.addWidget(self.lufs_val, 0, 2)
        meters.addWidget(QLabel("True peak"), 1, 0)
        self.tp_bar = QProgressBar()
        self.tp_bar.setRange(0, 100)
        self.tp_val = QLabel("–")
        meters.addWidget(self.tp_bar, 1, 1)
        meters.addWidget(self.tp_val, 1, 2)
        right.addWidget(meters_box)
        right.addStretch(1)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(120)
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
        def pct(v, lo, hi):
            if v is None or not isinstance(v, (int, float)):
                return 0
            return int(max(0, min(100, (v - lo) / (hi - lo) * 100)))
        self.lufs_bar.setValue(pct(lufs, -30.0, 0.0))
        self.tp_bar.setValue(pct(tp, -12.0, 0.0))
        self.lufs_val.setText("–" if lufs is None else f"{lufs:.2f} LUFS")
        self.tp_val.setText("–" if tp is None else f"{tp:.2f} dBTP")


def _selftest():
    """Headless smoke test of the *packaged* app: build the window offscreen and
    confirm the engine is reachable, then exit. Run as `Keel.exe --selftest` in
    CI (and locally) to prove a frozen build actually imports Qt + the engine."""
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication(sys.argv)
    KeelWindow()
    print(f"Keel selftest OK — engine {keel.__version__}, "
          f"presets {sorted(keel.PRESETS)}")
    app.quit()
    return 0


def main():
    if "--selftest" in sys.argv[1:]:
        return _selftest()
    app = QApplication(sys.argv)
    win = KeelWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
