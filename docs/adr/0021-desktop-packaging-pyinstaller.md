# ADR-0021: Desktop packaging — PyInstaller (Win onefile / macOS .app)

- Status: Accepted
- Date: 2026-06-16
- Deciders: Felipe Carvajal Brown

## Context

The GUI must ship as runnable executables to non-technical musicians — no Python
install. The packager must handle PySide6 + the native engine deps (numpy/scipy/
soundfile/pedalboard) and produce the right artifact per OS.

## Decision

Use **PyInstaller** via a single `Keel.spec` that branches per OS:

- **Windows:** a single **onefile** `Keel.exe` (easy to hand around).
- **macOS:** a **onedir `Keel.app`** bundle — *not* onefile, because onefile
  inside a `.app` is deprecated (blocked in PyInstaller 7) and penalised by
  macOS security scanning; the `.app` is then wrapped in a `.dmg`.

`gui.py` gains a `--selftest` path so the **frozen** app can verify headlessly
(imports Qt + the engine, exits 0) — used locally and in CI.

## Consequences

- One spec, two correct per-OS formats.
- The self-test catches a broken bundle before it ships.
- The `.exe`/`.app` are currently **unsigned** — code-signing / notarization is
  still open (tracked in the roadmap).

## References

- `Keel.spec`; `gui.py` `_selftest`; `requirements-build.txt`.
- Related: [ADR-0022](0022-ci-build-pipeline.md).
