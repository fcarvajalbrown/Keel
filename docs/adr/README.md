# Architecture Decision Records

This folder records the **decisions** behind Keel — why the engine, the config
surface, the tooling, and the product are shaped the way they are. Each ADR is
one decision: its context, the choice made, and the consequences. They are
append-only history; when a decision changes, add a new ADR that supersedes the
old one (don't rewrite it).

Format: [Michael Nygard's ADR template](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions).
Status values: `Accepted`, `Superseded by ADR-NNNN`, `Deprecated`.

## Index

### DSP core
- [ADR-0001](0001-scope-balance-and-master-only.md) — Scope: balance + master only, no tone shaping in the mix
- [ADR-0002](0002-deterministic-no-ml.md) — Deterministic engine, no ML, no randomness in the render path
- [ADR-0003](0003-master-loudness-target.md) — Master target -14 LUFS, true-peak ceiling -1 dBTP
- [ADR-0004](0004-internal-anchor-and-relative-balance.md) — Per-stem internal anchor -20 LUFS + relative LU balance
- [ADR-0005](0005-master-chain-clip-then-limit.md) — Master chain: oversampled soft-clip then true-peak limiter
- [ADR-0006](0006-oversampled-true-peak.md) — 4x polyphase-FIR oversampling for true-peak metering/limiting

### Engine behaviour
- [ADR-0007](0007-group-delivery.md) — Arbitrary labels, balanced as groups, printed image preserved
- [ADR-0008](0008-token-label-autodetect.md) — Filename label auto-detect via anchored token matching + scan review
- [ADR-0009](0009-optional-matchering-reference.md) — Optional Matchering reference-master path
- [ADR-0010](0010-24-bit-no-dither.md) — 24-bit output, dither deferred
- [ADR-0011](0011-recipes-defaults-deep-merge.md) — recipes.py defaults + deep-merge override model
- [ADR-0012](0012-keel-json-source-of-truth.md) — keel.json as the per-project source of truth

### Architecture / config
- [ADR-0013](0013-keel-py-library-facade.md) — keel.py library facade: one core, don't fork the DSP
- [ADR-0014](0014-named-master-presets.md) — Named master presets (target-only, render-time override)
- [ADR-0015](0015-bus-glue-off-by-default.md) — Bus glue wired but off by default
- [ADR-0016](0016-engine-delivery-agnostic.md) — Engine stays delivery-agnostic (no project assumptions)

### Tooling / build
- [ADR-0017](0017-offline-vendored-deps.md) — Offline-first vendored dependencies + venv workflow
- [ADR-0018](0018-stdlib-unittest-suite.md) — Stdlib unittest test suite, synthesized stems
- [ADR-0019](0019-gui-toolkit-pyside6.md) — GUI toolkit: PySide6 over Kivy / Tkinter
- [ADR-0020](0020-gui-deps-online-not-vendored.md) — GUI dependencies installed online, not vendored
- [ADR-0021](0021-desktop-packaging-pyinstaller.md) — Desktop packaging: PyInstaller (Win onefile / macOS .app)
- [ADR-0022](0022-ci-build-pipeline.md) — CI build pipeline: GitHub Actions, manual/tag trigger, self-test gate

### Product / licensing
- [ADR-0023](0023-dual-licensing.md) — Dual licensing: AGPL-3.0 + commercial
- [ADR-0024](0024-distribution-and-pricing.md) — Distribution & pricing: paid GUI (~USD 20) via GitHub Pages
