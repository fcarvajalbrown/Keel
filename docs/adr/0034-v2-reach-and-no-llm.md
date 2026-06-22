# ADR-0034: v2.0 reach direction (mobile + web) and the no-LLM boundary

- Status: Accepted
- Date: 2026-06-22
- Deciders: Felipe Carvajal Brown

## Context

Beyond the desktop GUI + VST3, the long-term goal is to reach phones and the web.
The paths differ in how faithfully they can carry Keel's deterministic,
exact-spec master, since the byte-identical engine is Python and the plugin chain
is an approximate C++ port (ADR-0029). A tempting iOS angle — leaning on Apple
Intelligence / an on-device LLM — was also raised.

## Decision

Target reach in the sequence **Android -> iOS -> web** (post-1.0; web is the
least-committed "maybe" stage):

- **Android** (first): standalone JUCE app (no plugin-host standard); runs the
  **approximate C++ chain**, not the exact engine.
- **iOS** (second): JUCE **AUv3** extension reusing the C++ plugin chain in iOS
  DAWs. Approximate.
- **Web** (maybe, last): if pursued, run the **existing Python engine
  server-side** (upload stems -> master) — the only surface that preserves the
  **exact guaranteed-spec** master. A client-side WASM port is rejected (it would
  give only the approximate chain).

The iOS build **does NOT use Apple Intelligence / an on-device LLM**. That is ML —
Keel's hardest non-goal (ADR-0002). An LLM-driven mastering tool is a **separate
product in its own repo**, not Keel.

## Consequences

- Mobile trades exactness for reach; only the web path keeps the byte-identical spec.
- Android-first is the heaviest build with the weakest host integration (decided
  deliberately, not by ease).
- Reaffirms the deterministic / no-ML identity (ADR-0002) at the platform boundary.

## References

- `ROADMAP.md` v2.0.
- Related: [ADR-0002](0002-deterministic-no-ml.md),
  [ADR-0029](0029-plugin-self-contained-master.md).
