# ADR-0038: Automated Python<->C++ DSP parity harness as the v0.9 freeze gate

- Status: Accepted
- Date: 2026-07-18
- Deciders: Felipe Carvajal Brown

## Context

The DSP SYNC RULE (ADR-0029) states that `mastering.py` and the plugin's C++ live
chain are **two disconnected implementations of the same master character**, kept
aligned by hand: after any master-math change you are supposed to mirror it into
both and re-A/B the same file by ear. That is a manual promise. It has held so far
because master-math changes have been rare, but v0.8 (ADR-0037) adds two fresh
ones, and v1.0 will **freeze** the DSP. Freezing a manually-kept-in-sync pair
without an objective parity check is exactly the "two-disconnected-impls risk" the
roadmap already flags as a caveat on the freeze.

The two chains cannot be expected to *null* — the C++ limiter is a different
implementation from pedalboard's and was never meant to be sample-identical (only
same character, approximate loudness, per ADR-0029). So the check must be
**tolerance-based**, not a bit-exact null.

## Decision

Make **`v0.9.0-beta`** a dedicated **DSP settle & freeze-prep** milestone that adds
no new master math and instead proves the engine stable. Its deliverables:

1. **Automated Python<->C++ parity harness.** Render a fixed battery of test
   signals through `mastering.py` and through the C++ chain (a small headless
   render path built from the plugin sources), measure the deltas
   (integrated LUFS, true-peak, and a coarse spectral/RMS-per-band difference),
   and **assert each is within an agreed tolerance**. Wire it into CI so a drift
   between the two implementations fails the build. This converts the manual DSP
   SYNC promise into an enforced gate.
2. **Golden-file regression tests** for stereo-width + tilt at representative
   settings (including off/neutral), locking their output so nothing drifts them
   accidentally later. Consistent with the existing determinism tests.
3. **True-peak stress validation** with width + tilt engaged at extreme settings
   across the real deliveries, confirming the -1 dBTP guarantee still holds.
4. **A written frozen-DSP spec sheet** enumerating every master stage, coefficient,
   and order — the precise reference the 1.0 freeze is declared against.
5. **By-ear A/B sign-off** on the carve-outs (user task).
6. **A freeze-candidate ADR** at the end of v0.9 declaring the DSP ready to freeze
   and naming any residual parity tolerance as a known, measured quantity.

## Consequences

- The 1.0 DSP freeze stamps an engine whose two implementations are proven within a
  measured tolerance, not merely assumed aligned — the freeze becomes safe.
- The DSP SYNC RULE gains teeth: future master-math changes are checked by CI, not
  only by discipline. (The rule text in CLAUDE.md stays; this makes it enforceable.)
- Tolerances are an explicit, documented number, not an implicit hope; the "barely
  limits at -14" and "same character" claims become auditable.
- Building a headless C++ render path is real engineering, but it reuses the plugin
  sources and pays for itself as a permanent regression guard.
- v0.9 carries no new master math, so it triggers no *new* DSP-SYNC obligation of
  its own — it only verifies the ones from v0.8.

## Alternatives considered

- **Keep parity manual (by-ear only), just add golden-file tests + a freeze ADR.**
  Smaller milestone, but leaves the freeze resting on an unmeasured promise for a
  pair of implementations that just changed. Rejected — the automated harness is
  the actual de-risking of the freeze.
- **Bit-exact null test.** Impossible by design (different limiter implementations,
  ADR-0029). Rejected in favor of tolerance-based parity.

## References

- `ROADMAP.md` "Road to 1.0" (`v0.9.0-beta`).
- Related: [ADR-0029](0029-plugin-self-contained-master.md) (the DSP SYNC RULE this
  enforces), [ADR-0037](0037-stereo-width-and-tilt-into-v08.md) (the v0.8 changes
  it verifies), [ADR-0036](0036-release-ladder-v07-to-v10.md) (the ladder),
  [ADR-0018](0018-stdlib-unittest-suite.md) (the existing test-suite style it
  extends).
