# Releasing Keel

How a Keel release is cut, and the rule for its annotated release notes.

## Rule: one notes text, used by every release

**Every release — built by CI or locally — MUST carry the same annotated notes
text, and that text lives in exactly one place: [`release-notes.md`](release-notes.md).**

- CI reads it (`gh release create --notes-file docs/release-notes.md`).
- A manual/local release reads the *same* file (see below).

So there is nothing to keep in sync by hand: edit `docs/release-notes.md` and
both paths pick it up. Update that file when the project state changes — e.g.
drop the "Pre-alpha" wording on leaving alpha, and remove the unsigned heads-up
once builds are signed/notarized. (The release *title* — `Keel <tag>
(pre-alpha)` — is set with `--title`, separate from the notes body.)

## How releases are published (CI, on a version tag)

`.github/workflows/build-app.yml` is the pipeline. On a `v*` tag push it:

1. Builds the Windows portable `Keel.exe`, the Inno installer
   `KeelSetup-<ver>.exe`, and the macOS (arm64) `Keel.dmg`. Each is gated by
   `--selftest` before upload.
2. Runs the `release` job, which checks out the repo and publishes a prerelease
   with `--notes-file docs/release-notes.md` and the three artifacts.

## Cutting a release (the normal path)

1. Bump the version in **`keel.py`** (`__version__`) and **`installer/keel.iss`**
   (`MyAppVersion`, kept in sync). The installer filename + version are read from
   `keel.py __version__`.
2. Commit the bump (`chore(release): bump version to X.Y.Z`) and push `main`.
3. Tag and push: `git tag -a vX.Y.Z-alpha -m "..." && git push origin vX.Y.Z-alpha`.
4. CI builds all three artifacts and publishes the prerelease automatically.
   Verify with `gh release view vX.Y.Z-alpha`.

## Building / releasing locally (Windows)

To rebuild the local artifacts (e.g. to test before tagging):

```powershell
.\.venv\Scripts\pyinstaller.exe Keel.spec --noconfirm          # dist\Keel.exe
$ver = (Select-String keel.py -Pattern '__version__\s*=\s*"([^"]+)"').Matches[0].Groups[1].Value
& "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" /DMyAppVersion=$ver installer\keel.iss
# -> dist\KeelSetup-<ver>.exe
```

If you publish a release **by hand**, use the same notes file so the rule holds
(macOS `Keel.dmg` only comes from CI):

```powershell
gh release create vX.Y.Z-alpha --prerelease `
  --title "Keel vX.Y.Z-alpha (pre-alpha)" `
  --notes-file docs/release-notes.md `
  dist\Keel.exe dist\KeelSetup-X.Y.Z.exe
```

Prefer the tag + CI path when you can — it also builds and attaches the macOS
`Keel.dmg`. `dist/` is gitignored; local builds are not committed.

## Version lineage

- `v0.1.0-alpha` — first pre-alpha (engine + GUI scaffold + CI).
- `v0.2.0-alpha` — standalone GUI restyle (dark teal theme, custom meters,
  Space Grotesk branding + app icon, fader/close fixes, reset button).
- `v0.3` — plugin / VST work (separate workstream).
