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
(alpha)` — is set with `--title`, separate from the notes body.)

## How releases are published (CI, on a version tag)

`.github/workflows/build-app.yml` is the pipeline. On a `v*` tag push it:

1. Builds the Windows portable `Keel.exe`, the Inno installer
   `KeelSetup-<ver>.exe`, and the macOS (arm64) `Keel.dmg`. Each is gated by
   `--selftest` before upload.
2. Runs the `release` job, which checks out the repo and publishes a prerelease
   with `--notes-file docs/release-notes.md` and the three artifacts.

## Cutting a release (the normal path)

1. Bump the version in **`keel.py`** (`__version__`), **`installer/keel.iss`**
   (`MyAppVersion`), AND **`plugin/CMakeLists.txt`** (`project(... VERSION ...)`).
   These are versioned in lockstep — the GUI and the VST3 always share one version
   (see CLAUDE.md "Versioning (STRICT)"). The installer filename + version are read
   from `keel.py __version__`.
2. Commit the bump (`chore(release): bump version to X.Y.Z`) and push `main`.
3. Tag and push: `git tag -a vX.Y.Z-alpha -m "..." && git push origin vX.Y.Z-alpha`.
4. CI builds the three GUI artifacts and publishes the prerelease automatically.
   Verify with `gh release view vX.Y.Z-alpha`, and **wait for the run to finish**
   (`gh run watch`) before announcing it.
5. **The VST3 plugin is not built by CI.** Build it locally
   (`plugin\build.ps1 -Clean`), zip `Keel.vst3` as `Keel-VST3-windows-X.Y.Z.zip`,
   and attach it to the published release:
   `gh release upload vX.Y.Z-alpha dist\Keel-VST3-windows-X.Y.Z.zip`.
6. **Sweep the docs** so no README/doc points at a stale version or release-asset
   URL (the README download buttons link a versioned installer asset).

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
  --title "Keel vX.Y.Z-alpha (alpha)" `
  --notes-file docs/release-notes.md `
  dist\Keel.exe dist\KeelSetup-X.Y.Z.exe dist\Keel-VST3-windows-X.Y.Z.zip
```

Prefer the tag + CI path when you can — it also builds and attaches the macOS
`Keel.dmg`. `dist/` is gitignored; local builds are not committed.

## Version lineage

- `v0.1.0-alpha` — first pre-alpha (engine + GUI scaffold + CI).
- `v0.2.0-alpha` — standalone GUI restyle (dark teal theme, custom meters,
  Space Grotesk branding + app icon, fader/close fixes, reset button).
- `v0.3.0-alpha` — first Keel VST3 plugin (self-contained real-time master,
  Windows preview) shipped alongside the app; GUI + plugin now versioned in
  lockstep.
- `v0.4.0-beta` — Harden & CI: graceful degradation on bad input (corrupt audio /
  malformed keel.json / NaN / silent) + edge-case tests; expanded instrument set
  (piano, organ/keys, backing vocals, aux percussion) with an editable instrument
  dropdown in the GUI; the test suite runs as a CI gate (Win + macOS) and the VST3
  plugin is built + pluginval-smoke-tested in CI, so one tag ships GUI + plugin.
- `v0.5.0-beta` — Plugin parity + macOS plugin: the plugin now builds for macOS
  (VST3 + AU for Logic / GarageBand) alongside Windows, both pluginval-validated in
  CI; the Bus-glue toggle is wired to the master glue comp (default on); the dead
  Reference toggle becomes a passive reference loudness/peak readout measured with
  libebur128 (canonical BS.1770, matches the CLI/GUI numbers). CI also auto-prunes
  old prerelease assets (keeps the newest two) to stay under storage quota.
