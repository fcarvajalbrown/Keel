# ADR-0033: Oversampling selector on the plugin live chain only

- Status: Accepted
- Date: 2026-06-22
- Deciders: Felipe Carvajal Brown

## Context

Keel runs a fixed 4x oversampling for the soft-clip + true-peak limiter
(ADR-0006). Pros expect to see and sometimes control oversampling quality. But on
the deterministic CLI/GUI path, a user-variable factor would break "same stems +
recipe = identical output" (ADR-0002) — the byte-identical guarantee depends on a
fixed factor.

The plugin's live master is already an *approximate* real-time chain (ADR-0029),
not the byte-identical engine, so a quality/CPU selector there changes nothing that
was ever guaranteed.

## Decision

Allow a **quality/oversampling selector on the plugin's live chain only**. The
**CLI/GUI path stays fixed** (visible, not variable). No DSP-SYNC concern: the
reference master math is unchanged; the selector only trades the plugin's live CPU
cost against alias suppression, which is already approximate.

## Consequences

- Plugin users get a CPU-vs-quality control without touching the guaranteed spec.
- The determinism promise on the CLI/GUI is untouched.
- Upholds ADR-0002 / ADR-0006 on the deterministic path while easing the plugin.

## References

- `ROADMAP.md` v0.5 candidates + non-goals.
- Related: [ADR-0002](0002-deterministic-no-ml.md),
  [ADR-0006](0006-oversampled-true-peak.md),
  [ADR-0029](0029-plugin-self-contained-master.md).
