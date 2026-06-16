# ADR-0018: Stdlib unittest test suite, synthesized stems

- Status: Accepted
- Date: 2026-06-16
- Deciders: Felipe Carvajal Brown

## Context

The engine's guarantees (determinism, exact loudness landing, group balance,
label matching) were unverified by any automated check. A test suite was needed,
but adding a test framework (pytest) would mean another dependency to vendor for
the offline-first install — and pytest had no cp314 wheel in the venv.

## Decision

Write the suite with the **stdlib `unittest`** runner — zero new dependency, runs
via `python -m unittest discover -s tests`. Tests **synthesize tiny sine stems on
the fly** (no committed audio) and assert: byte-identical determinism, exact
master LUFS under the true-peak ceiling (incl. via a preset), the group-balance
invariant, the mono+stereo regression, >2-channel coercion, label tokenization,
recipe deep-merge, and the user-preset store.

## Consequences

- A safety net that costs no extra dependency and ~2s to run.
- No audio fixtures to store or license.
- pytest-only conveniences are unavailable, accepted for the dependency win.

## References

- `tests/test_engine.py`.
- Related: [ADR-0002](0002-deterministic-no-ml.md), [ADR-0017](0017-offline-vendored-deps.md).
