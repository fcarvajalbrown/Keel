# Next-agent prompt — Keel

You are picking up work on **Keel**, a deterministic automix + automaster engine
(stems in -> balanced mix + loudness-safe master out). The long-term goal is a
**standalone GUI** and a **VST/plugin**. The CLI engine is done and validated,
including arbitrary-label stems: any number of files, labels auto-detected into an
editable per-song `keel.json`, files sharing a label balanced as one group.

## Do this first, before writing any code

1. **Read these, in order:** `CLAUDE.md` (scope, locked DSP, conventions),
   `ROADMAP.md` (where we are and what's next), `README.md` (the product story).
   Do not skip them — they encode decisions already made.
2. **Locate the current phase in `ROADMAP.md`.** Phases 0-1 (engine core +
   song-agnostic standalone) are DONE. The next open phase is **Phase 2 —
   validate on real-world material**, then Phase 3 (config/presets), Phase 4
   (GUI), Phase 5 (VST), Phase 6 (distribution).
3. **Confirm direction with the user before proceeding.** Do not assume the next
   roadmap phase is what they want today. Ask what they want to tackle this
   session and tailor to their answer. Present the choice using the **interactive
   arrow-select option UI (the blue selector), not a plain-text list** — this is a
   firm preference (see CLAUDE.md). Offer the logical next phases as options.

## How the user likes to work (match this)

- **Decisions -> arrow-select UI.** Every fork, however small, goes through the
  blue interactive option selector. Chain calls if there are more than 4
  questions. Only fall back to text if the UI is unavailable.
- **No emojis** anywhere (docs, commits, code, chat). Plain text only.
- **Conventional + logical commits.** `type(scope): summary`; one atomic,
  self-contained change per commit. See CLAUDE.md.
- **Research-before-tweak for DSP.** Before changing the mixing/mastering
  *approach* (loudness target, limiter design, reference-matching), do ~5 web
  searches and cite them. Do not tune DSP from memory.
- **Marketing audience is broad:** lead with simplicity for bedroom/solo
  producers, surface the LUFS/true-peak rigor for working engineers underneath.

## Hard guardrails (do not violate)

- Scope is **balance + master only**. No tone shaping in the mix stage (stems are
  pre-treated), no stem separation, no ML, no randomness in the render path.
- Keep `mixer.py` / `mastering.py` / `meters.py` project-agnostic — they already
  are. Do not reintroduce song lists, a fixed set of stem types, or folder
  assumptions (that coupling was removed on 2026-06-14; labels are arbitrary and
  driven by each song's `keel.json`).
- Locked DSP defaults: master **-14.0 LUFS / -1.0 dBTP**, internal anchor
  **-20 LUFS**. Change only deliberately, with research.
- Never hand-edit files in `out/` — build artifacts.

## Open items worth raising with the user

- **Folder rename (do this):** the repo still lives in `C:\Projects\temp`; rename
  it to `C:\Projects\keel`. It cannot be done from inside a live session (Windows
  locks the working directory). Steps for the user:
  1. Close Claude Code (and any editor/terminal with `C:\Projects\temp` open).
  2. Rename the folder: `Rename-Item C:\Projects\temp C:\Projects\keel`
  3. Reopen Claude Code in `C:\Projects\keel` and continue.
  Nothing in the code depends on the folder name (paths come from `__file__` / CLI
  args), and the git remote is unaffected. Caveat: the memory project key changes
  from `C--Projects-temp` to `C--Projects-keel`, so prior memories won't auto-load
  under the new path — re-save the "never add Claude as co-author" rule on the
  first session in the renamed folder.
- **License:** done — **AGPL-3.0 + dual commercial**. `LICENSE` is the verbatim
  AGPLv3; per-file copyright headers (Felipe Carvajal Brown, 2026) are in place;
  `COMMERCIAL-LICENSE.md` holds the commercial terms + contact
  (fcarvajalbrown@gmail.com); README has a License section. Remaining only if
  desired: formal legal review and a dedicated licensing contact address.
- **Trademark:** "Keel" cleared initial web searches; verify formally in target
  markets before public launch.
- **GUI scaffolding (Phase 4):** keep the engine importable as a shared library
  so CLI, GUI, and plugin all drive one core. Do not fork the DSP.
- **Landing assets:** tagline/elevator pitch, logo/wordmark, before/after demo
  audio (not yet started).

## Quick sanity check (engine still runs)

```powershell
python -m py_compile recipes.py build.py mixer.py mastering.py meters.py
python build.py --help
python build.py --stems "C:\path\to\stems" --out out   # writes keel.json, renders
```

Start by reading the three docs, then ask the user (via the option UI) what this
session is for.
