# ADR-0017: Offline-first vendored dependencies + venv workflow

- Status: Accepted
- Date: 2026-06-14
- Deciders: Felipe Carvajal Brown

## Context

The engine's dependencies (numpy, scipy, soundfile, pyloudnorm, pedalboard, plus
optional matchering) are pip-only. Relying on PyPI at install time is a risk: a
package could be pulled (e.g. a vendor removing pedalboard), and an offline or
air-gapped machine couldn't reinstall.

## Decision

**Vendor the exact wheels** the engine needs in `vendor/` so it installs with no
internet, and provide `setup.ps1` to build a local `.venv` from them
(`-Online` to use PyPI instead, `-Matchering` for the optional reference path).
The `.venv` is never committed; it is rebuilt per machine. Wheels are pinned for
`cp314-win_amd64`.

## Consequences

- Reproducible, offline-capable installs of the core engine.
- Insurance against upstream packages disappearing.
- Platform-specific wheels must be re-vendored for a different OS/Python.
- The heavyweight GUI stack is the deliberate exception (see [ADR-0020](0020-gui-deps-online-not-vendored.md)).

## References

- `vendor/README.md`; `setup.ps1`; `requirements.txt`.
- Related: [ADR-0009](0009-optional-matchering-reference.md), [ADR-0020](0020-gui-deps-online-not-vendored.md).
