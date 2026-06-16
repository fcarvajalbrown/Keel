# ADR-0009: Optional Matchering reference-master path

- Status: Accepted
- Date: 2026-06-14
- Deciders: Felipe Carvajal Brown

## Context

Some users want a master that matches the tonal balance and loudness of a
specific commercial reference track, rather than Keel's internal target-driven
chain. Matchering does exactly that, but it drags a heavy numba / llvmlite /
pandas tree.

## Decision

Provide an **optional** reference-master path: if a reference file is supplied,
`mastering.py` uses Matchering to match the mix to it (RMS, frequency response,
peak, stereo width). On this path the **reference sets the loudness**, so
`target_lufs` is ignored. It is **not installed by default** — the internal chain
is the default — and is selected via `--ref` / the GUI reference picker.

## Consequences

- Two clearly separated master paths; the default stays light.
- Matchering is vendored for offline install but opt-in (`setup.ps1 -Matchering`).
- Reference quality matters: a genre/tempo-matched reference per song is needed;
  one reference reused across songs skews the result.

## References

- `mastering.py` `_reference_master`; `CLAUDE.md` master chain note.
- Related: [ADR-0017](0017-offline-vendored-deps.md).
