# ADR-0019: GUI toolkit — PySide6 over Kivy / Tkinter

- Status: Accepted
- Date: 2026-06-16
- Deciders: Felipe Carvajal Brown

## Context

The standalone GUI (Phase 4) needs a Python toolkit that: installs on the
project's **Python 3.14**, looks native on Windows/macOS desktop, can draw live
meters/faders, and — because the GUI is the **paid** product (ADR-0024) — links
into a **closed, commercially-licensed** build. Candidates: Tkinter (stdlib),
Kivy, PySide6/Qt, PyQt.

## Decision

Use **PySide6 (Qt)**. Decisive findings:

- **Kivy — ruled out:** no cp314 wheels; it fails to install on Python 3.14.
- **PyQt — ruled out on license:** GPL, which is incompatible with selling a
  closed commercial build without a commercial Qt license.
- **PySide6 — chosen:** ships a stable-ABI (`abi3`) wheel that runs on 3.14,
  looks native, and is **LGPL**, so it links into a closed commercial build.
- Tkinter (stdlib) was the offline-safe fallback but was passed over for Qt's
  native widgets, file dialogs, and meters.

## Consequences

- The GUI installs and runs on the same 3.14 the engine uses.
- Licensing is clean for the dual-license/paid model.
- PySide6 is large (~150 MB), handled by [ADR-0020](0020-gui-deps-online-not-vendored.md).

## References

- `gui.py`; `ROADMAP.md` Phase 4 toolkit note.
- Related: [ADR-0023](0023-dual-licensing.md), [ADR-0024](0024-distribution-and-pricing.md).
