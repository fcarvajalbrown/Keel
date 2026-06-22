# ADR-0030: Plugin Bus-glue toggle gated, default ON

- Status: Accepted
- Date: 2026-06-22
- Deciders: Felipe Carvajal Brown

## Context

The plugin exposed a "Bus Glue" toggle (`glue` parameter), but `processBlock`
ran the glue compressor unconditionally — the toggle did nothing. The plugin's
glue comp is the C++ mirror of `mastering.py`'s master tone-stage compressor
(-14 dB / 1.6:1 / 30 ms / 250 ms), which the Python engine applies **always-on**
as part of the locked master character (ADR-0003/ADR-0005). So the plugin's glue
is the *master* glue, not the mixer's off-by-default bus glue (ADR-0015).

This created a DSP-SYNC trap: the param default was `false`, but because the comp
ran regardless, the plugin happened to match Python. Naively wiring the toggle and
leaving the default `false` would have *introduced* drift — the out-of-box plugin
master would drop a compressor `mastering.py` always applies.

## Decision

Gate `glueComp` on the `glue` parameter, and **flip the default to ON** so the
out-of-box plugin master still matches `mastering.py`. Turning it OFF is a
deliberate, clearly-labelled plugin-only deviation with no CLI/GUI counterpart. No
Python change was needed; default-on preserves parity, so the DSP SYNC RULE
(ADR-0029) is honoured without mirroring.

## Consequences

- The toggle now functions; the default master is unchanged and still in sync.
- "Glue OFF" is a plugin-only state — there is no exact CLI/GUI equivalent.
- By-ear A/B (plugin vs a `build.py` render) remains the user's sign-off.

## References

- `plugin/Source/PluginProcessor.cpp` (`makeParameterLayout`, `processBlock`).
- Related: [ADR-0015](0015-bus-glue-off-by-default.md) (mixer bus glue — distinct),
  [ADR-0029](0029-plugin-self-contained-master.md) (DSP SYNC RULE).
