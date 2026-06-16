# ADR-0013: keel.py library facade — one core, don't fork the DSP

- Status: Accepted
- Date: 2026-06-16
- Deciders: Felipe Carvajal Brown

## Context

Keel will grow multiple front-ends — CLI (done), GUI, and a VST/plugin. The
danger is each front-end importing engine internals differently, or worse,
copying DSP, so the cores drift apart.

## Decision

Provide a single public library facade, **`keel.py`**: `import keel` exposes the
engine's public surface (`mix`, `master`, recipes, presets, meters). Every
front-end drives this one module; the DSP is **never forked** per front-end. The
facade adds no behaviour of its own — it only re-exports.

## Consequences

- CLI, GUI, and future plugin share exactly one engine; fixes land once.
- A stable import surface decouples front-ends from internal module layout.
- New engine capabilities must be surfaced through `keel.py` to be "public".

## References

- `keel.py`; `ROADMAP.md` Phase 4 (engine importable as a library).
- Related: [ADR-0019](0019-gui-toolkit-pyside6.md), [ADR-0021](0021-desktop-packaging-pyinstaller.md).
