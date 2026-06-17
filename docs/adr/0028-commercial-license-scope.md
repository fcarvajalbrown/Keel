# ADR-0028: Commercial license scope — labels, studios, and pro client work pay; the GUI is not "paid"

- Status: Accepted (supersedes ADR-0025)
- Date: 2026-06-17
- Deciders: Felipe Carvajal Brown

## Context

ADR-0025 set the hybrid model: the engine stays AGPL-3.0, the GUI is free for
non-commercial use and for individual musicians making their own music (PolyForm
Noncommercial + grant), funded by donations, with a USD 20/seat commercial license
required for "business / redistribution" use.

Two problems with how that landed:

1. **The framing read as "we charge for the GUI."** A "GUI: free for
   non-commercial" badge sat next to a "commercial use: USD 20/seat" badge, which
   invites the reading that the app itself is the paywalled product. It is not. The
   GUI is free; the fee is a **commercial-use license** for specific parties.
2. **"business / redistribution" was too vague** about *who* actually pays. We want
   to name them: the people who use Keel to earn from **other people's** material,
   or to build a business on it.

The legal basis is unchanged from ADR-0025: AGPL cannot restrict commercial use, so
the GUI is source-available under PolyForm Noncommercial plus a grant, with a
separate commercial license. The author holds copyright on all original code.

## Decision

The pay/free line is drawn by **whose music you are working on and whether you are
running a business on Keel** — not by whether you are a professional.

**Free (no payment, ever):**

- **Individuals making their own music** — hobbyist or professional artist —
  including selling, streaming, and distributing those works. A professional who
  mixes/masters **their own** records pays nothing.
- All **non-commercial use** (PolyForm Noncommercial: personal, hobby, study,
  charitable / educational / public organizations).

**A commercial license is required (USD 20, one-time, per seat — unchanged):**

- **Record labels.**
- **Professional mixing / mastering studios**, and **freelance mix / master
  engineers**, using Keel to process **other people's material as a paid service**
  (paid client work, at commercial scale).
- **Companies** offering Keel's functionality as a **paid product or service**
  (hosted, bundled, embedded, or resold).
- **Redistributing the GUI** (modified or not) inside another product.
- Building the **AGPL engine** into a **closed-source** product/service without
  meeting the AGPL's copyleft obligations.

**The test:** are you using Keel on **your own** music (free), or to **earn from
others' material / run a business on it** (commercial license)? Being a pro does
not by itself trigger the fee — doing paid client work or operating as a
label/studio/business does.

**Framing rule (load-bearing for all project copy):** never describe this as
"paying for the GUI." The GUI is free. What is sold is a **commercial-use license**
for the parties above. Project copy should lead with "free for musicians making
their own music" and describe the fee as commercial-use, not as the price of the
app.

Price and mechanism are unchanged from ADR-0025 (USD 20/seat, perpetual, no
subscription; volume/site licensing on request; donations fund development and
grant no commercial rights).

## Consequences

- Wording is swept to name the paying parties and drop the "paid GUI" reading
  across the core licensing surface: `COMMERCIAL-LICENSE.md`,
  `LICENSE-NONCOMMERCIAL.md`, and the README (EN + ES) License + Support sections.
  The redundant "GUI: free for non-commercial" badge is removed (the commercial-use
  badge already carries the split).
- **`LICENSE-GUI.md` is renamed to `LICENSE-NONCOMMERCIAL.md`.** The old name
  implied the GUI was the licensed/paid thing; everyone gets the app, and the file
  is really the non-commercial-use license — the counterpart to
  `COMMERCIAL-LICENSE.md`. All references updated (READMEs, COMMERCIAL-LICENSE.md,
  per-file headers in `gui.py` / `gui_theme.py` / `userpresets.py`, installer
  `LicenseFile`, ADR index).
- No change to the licenses themselves (AGPL engine; PolyForm + grant GUI; separate
  commercial license) or to the price — this ADR sharpens **scope and framing**,
  not the legal structure.
- Enforcement remains honor-plus-license; the named scope makes the boundary easier
  to self-assess (own music vs paid client work / business).
- Supersedes ADR-0025's looser "business / redistribution" wording; ADR-0025 stays
  as history.

## References

- Supersedes: [ADR-0025](0025-gui-noncommercial-license-and-donations.md).
- Related: [ADR-0023](0023-dual-licensing.md),
  [ADR-0024](0024-distribution-and-pricing.md).
- `COMMERCIAL-LICENSE.md`, `LICENSE-NONCOMMERCIAL.md` (renamed from
  `LICENSE-GUI.md`), `README.md` / `README.es.md` (License + Support).
- PolyForm Noncommercial 1.0.0: <https://polyformproject.org/licenses/noncommercial/1.0.0>
