# Releasing Keel

How a Keel release is cut, and the **canonical release-notes text** that every
release must carry.

## Release-notes text (canonical)

Every GitHub release uses the text below. It is the single source of truth; the
CI workflow injects it automatically (see "How releases are published"), so a
normal tagged release gets it without any manual step. Keep this file and the
workflow in sync if you change the wording.

```markdown
**Pre-alpha** build of the Keel desktop GUI (deterministic automix + automaster).

## Downloads
- **Windows** — `KeelSetup-<ver>.exe` (recommended installer) or `Keel.exe` (portable).
- **macOS (Apple Silicon / arm64)** — `Keel.dmg`.

## Heads-up: these builds are unsigned
They are not yet code-signed, so the OS will warn on first launch:
- **Windows**: SmartScreen shows "Windows protected your PC" — click
  **More info -> Run anyway**.
- **macOS**: Gatekeeper blocks an unidentified developer — **right-click
  the app -> Open**, then confirm.

Signing/notarization is planned. See `ROADMAP.md` for status and
`README.md` for what Keel does.
```

Update this text when the project state changes — e.g. drop "Pre-alpha" when
leaving alpha, and remove the unsigned heads-up once builds are
signed/notarized.

## How releases are published (CI, on a version tag)

`.github/workflows/build-app.yml` is the pipeline. On a `v*` tag push it:

1. Builds the Windows portable `Keel.exe`, the Inno installer
   `KeelSetup-<ver>.exe`, and the macOS (arm64) `Keel.dmg`. Each is gated by
   `--selftest` before upload.
2. Runs the `release` job, which writes the notes text above into `notes.md` and
   runs `gh release create "<tag>" --title "Keel <tag> (pre-alpha)" --prerelease
   <assets>`.

So the notes text lives in the `notes.md` heredoc inside that workflow — that is
the copy CI actually publishes. This file is the human-readable record of it;
edit both together.

## Cutting a release (checklist)

1. Bump the version in **`keel.py`** (`__version__`) and **`installer/keel.iss`**
   (`MyAppVersion`, kept in sync). The installer filename + version are read from
   `keel.py __version__`.
2. Commit the bump (`chore(release): bump version to X.Y.Z`) and push `main`.
3. Tag and push: `git tag -a vX.Y.Z-alpha -m "..." && git push origin vX.Y.Z-alpha`.
4. CI builds all three artifacts and publishes the prerelease automatically.
   Verify with `gh release view vX.Y.Z-alpha`.

## Version lineage

- `v0.1.0-alpha` — first pre-alpha (engine + GUI scaffold + CI).
- `v0.2.0-alpha` — standalone GUI restyle (dark teal theme, custom meters,
  Space Grotesk branding + app icon, fader/close fixes, reset button).
- `v0.3` — plugin / VST work (separate workstream).
