# ADR-0003: Master target -14 LUFS, true-peak ceiling -1 dBTP

- Status: Accepted
- Date: 2026-06-14
- Deciders: Felipe Carvajal Brown

## Context

Streaming platforms normalize playback loudness, so mastering "as loud as
possible" just gets turned back down — often with transients already destroyed
by a slammed limiter. A sane default target is needed that is competitive,
clean, and safe across platforms.

## Decision

Default master target **-14.0 LUFS integrated**, true-peak ceiling **-1.0 dBTP**.
This is the normalization target for Spotify / YouTube / Tidal / Amazon, and it
stays clean through Keel's limiter. The -1 dBTP ceiling leaves headroom so lossy
transcoding (AAC/Ogg) does not clip. The chain *can* push louder (-10/-11)
cleanly when asked (see [ADR-0014](0014-named-master-presets.md)), but -14 is the
default.

## Consequences

- Out-of-the-box masters are streaming-optimal and undistorted.
- Research-cited and re-validated against current platform norms before any
  change ("research-before-tweak" rule).
- Louder targets are opt-in via presets/CLI, not the default.

## References

- `CLAUDE.md` — "Locked DSP decisions".
- Platform loudness research captured in [ADR-0014](0014-named-master-presets.md).
- Related: [ADR-0005](0005-master-chain-clip-then-limit.md).
