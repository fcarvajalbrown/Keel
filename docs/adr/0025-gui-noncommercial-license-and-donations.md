# ADR-0025: GUI is free (non-commercial) + donations; commercial use is USD 20/seat

- Status: Superseded by [ADR-0028](0028-commercial-license-scope.md) (supersedes ADR-0024)
- Date: 2026-06-17
- Deciders: Felipe Carvajal Brown

> **Superseded by [ADR-0028](0028-commercial-license-scope.md).** The hybrid model
> (AGPL engine, free GUI for own-music/non-commercial, USD 20/seat commercial
> license) stands; ADR-0028 sharpens *who* pays (record labels, professional
> mixing/mastering studios and freelance engineers doing paid client work,
> companies redistributing/reselling) and fixes the framing — the GUI is not the
> paid product; what is sold is a commercial-use license.

## Context

ADR-0024 made the packaged GUI a paid product (~USD 20) sold via a landing page.
On reflection that cuts against Keel's launch message — an anti-paywall tool for
musicians who count their pesos. We want the GUI to be **free for the people it
is built for**, funded by goodwill, while still charging the parties who can
afford it: businesses that build on Keel commercially.

The legal constraint (researched): **AGPL cannot restrict commercial use or
attach a per-use fee** — it permits commercial use outright. To make "commercial
use pays" actually enforceable you need a **source-available non-commercial
license** (e.g. PolyForm Noncommercial) plus a separate commercial license. The
author holds copyright on all original code, so future versions can be licensed
freely; past AGPL releases remain AGPL.

## Decision

A **hybrid** model:

- **Engine** (`keel.py`, `recipes.py`, `mixer.py`, `mastering.py`, `meters.py`,
  `build.py`) stays **AGPL-3.0** — unchanged, still open source.
- **Desktop GUI** (`gui.py`, `userpresets.py`, packaged `Keel.exe` / `Keel.app`)
  is **PolyForm Noncommercial 1.0.0** plus an **additional free-use grant**
  (`LICENSE-GUI.md`): free for all non-commercial use AND free for individual
  musicians making their own music, **including selling that music**.
- **Donations** fund development — PayPal link in the README and a GitHub
  Sponsor button (`.github/FUNDING.yml`). Voluntary; grant no commercial rights.
- **Commercial license** (`COMMERCIAL-LICENSE.md`): **USD 20, one-time, per
  seat**, perpetual, no subscription. Required only for **business /
  redistribution** use — paid product/service, studio/agency client work at
  commercial scale, redistributing the GUI in another product, or closed-source
  use of the AGPL engine.

The scope line: **make your own music with it for free; pay only if you run a
business on it.**

## Consequences

- The GUI is no longer "the paid product" — it is free donationware with a
  commercial-use license. This **supersedes ADR-0024**'s pricing/distribution.
- The GUI is now **source-available, not OSI open source**; the engine remains
  open source. Badges/README reflect the split.
- Donations to an individual via PayPal are not tax-deductible for donors and
  count as personal income (note for the author's taxes).
- A landing-page donate button + commercial-license checkout still need standing
  up (ROADMAP Phase 6).
- Enforcement of the non-commercial boundary is honor-plus-license; the
  additional grant is worded to keep individual musicians unambiguously free.

## References

- `LICENSE-GUI.md`, `COMMERCIAL-LICENSE.md`, `README.md` (License + Support),
  `.github/FUNDING.yml`, `ROADMAP.md` Phase 6.
- PolyForm Noncommercial 1.0.0: <https://polyformproject.org/licenses/noncommercial/1.0.0>
- Supersedes: [ADR-0024](0024-distribution-and-pricing.md).
- Related: [ADR-0023](0023-dual-licensing.md), [ADR-0019](0019-gui-toolkit-pyside6.md).
