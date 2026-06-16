# ADR-0015: Bus glue wired but off by default

- Status: Accepted
- Date: 2026-06-16
- Deciders: Felipe Carvajal Brown

## Context

A gentle bus-glue compressor over the summed mix can add cohesion. But Keel's
stems are already mix-ready (ADR-0001), so glue risks double-processing, and
whether it helps is an ear call that depends on the material.

## Decision

The glue compressor exists in `mixer.mix(glue=...)` but is **off by default**. It
is reachable through the config surface — `keel.json` `"glue": false` and a
`--glue/--no-glue` CLI override (CLI beats the mapping) — so it can be A/B'd, but
nothing changes when it is unset. The decision to ship it *on* for a given mix is
left to listening.

## Consequences

- No tone change by default; the scope boundary (ADR-0001) holds.
- The capability is one toggle away when a sum genuinely wants light cohesion.
- The "evaluate by ear" call remains an open, user-owned step.

## References

- `mixer.py` `mix(glue=...)`; `build.py --glue/--no-glue`.
- Related: [ADR-0001](0001-scope-balance-and-master-only.md).
