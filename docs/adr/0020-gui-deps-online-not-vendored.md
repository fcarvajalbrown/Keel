# ADR-0020: GUI dependencies installed online, not vendored

- Status: Accepted
- Date: 2026-06-16
- Deciders: Felipe Carvajal Brown

## Context

The core engine is offline-first with vendored wheels (ADR-0017). PySide6, the
GUI's only extra dependency, is ~150 MB of Qt binaries. Vendoring that into git
would bloat the repo permanently for an optional front-end.

## Decision

Do **not** vendor the GUI dependency. Install PySide6 **online**, opt-in, via
`setup.ps1 -Gui` / `requirements-gui.txt` — like the optional Matchering path.
The **core engine stays offline-vendored**; the GUI is an online extra.

## Consequences

- The repo stays lean; no 150 MB of Qt binaries in history.
- Building/running the GUI requires internet once (to install Qt).
- Consistent with treating the GUI as an optional layer over the engine.

## References

- `requirements-gui.txt`; `setup.ps1 -Gui`; `vendor/README.md` ("Not vendored").
- Related: [ADR-0017](0017-offline-vendored-deps.md), [ADR-0019](0019-gui-toolkit-pyside6.md).
