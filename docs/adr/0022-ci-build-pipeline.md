# ADR-0022: CI build pipeline — GitHub Actions, manual/tag trigger, self-test gate

- Status: Accepted
- Date: 2026-06-16
- Deciders: Felipe Carvajal Brown

## Context

A macOS app cannot be built on the Windows dev machine (PyInstaller does not
cross-compile). Both a Windows `.exe` and a macOS `.dmg` are needed as
downloadable, testable artifacts — and the maintainer does not want routine
commits spamming build-failure noise.

## Decision

A **GitHub Actions** matrix (`.github/workflows/build-app.yml`) builds on
`windows-latest` (-> `Keel.exe`) and `macos-latest`/arm64 (-> `Keel.dmg`). Key
choices:

- **Trigger: `workflow_dispatch` + version tags only** — never on push, so
  day-to-day commits don't trigger builds or failures.
- **`fail-fast: false`** — one OS failing doesn't cancel the other.
- **Self-test gate** — each job runs the frozen app's `--selftest` before upload,
  so a broken bundle fails its own job instead of shipping.
- **macOS arm64 only** — the only macOS arch with a cp314 `pedalboard` wheel;
  Intel would need a separate macos-13 + Python 3.13 job.
- Actions pinned to Node-24-native majors (checkout@v5, setup-python@v6,
  upload-artifact@v7) to stay annotation-free.

## Consequences

- Both executables are produced in the cloud; no Mac required to ship a Mac build.
- CI is quiet by default and validated green before hand-off.
- A separate Intel-mac job is a known, easy addition if needed.

## References

- `.github/workflows/build-app.yml`.
- Related: [ADR-0021](0021-desktop-packaging-pyinstaller.md), [ADR-0019](0019-gui-toolkit-pyside6.md).
