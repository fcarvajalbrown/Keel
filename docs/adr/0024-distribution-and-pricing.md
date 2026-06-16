# ADR-0024: Distribution & pricing — paid GUI (~USD 20) via GitHub Pages

- Status: Accepted
- Date: 2026-06-16
- Deciders: Felipe Carvajal Brown

## Context

The engine is free and open (ADR-0023), but the project needs a revenue path. The
packaged GUI app is the natural product: it turns the engine into something a
non-technical musician can run with one click.

## Decision

- The **engine stays AGPL-3.0** (free, open).
- The **packaged GUI app is the paid product**: a one-time low price (~**USD
  20**), sold under the commercial license (`COMMERCIAL-LICENSE.md`).
- It is sold from a **static landing site on GitHub Pages** (free hosting, no
  server) via a checkout/license link (e.g. Gumroad / Lemon Squeezy / Stripe
  Payment Link).
- This is lawful because the GUI stack is LGPL-safe (ADR-0019): PySide6 links
  into a closed commercial build.
- The same model applies later to the VST/plugin.

## Consequences

- Clear free-vs-paid split: open engine, paid convenience app.
- No infrastructure to run — a static site plus a payment link.
- Requires finishing code-signing/notarization (ADR-0021) and paying the relevant
  publication/signing fees before public sale.

## References

- `ROADMAP.md` Phase 6; `COMMERCIAL-LICENSE.md`.
- Related: [ADR-0023](0023-dual-licensing.md), [ADR-0019](0019-gui-toolkit-pyside6.md), [ADR-0021](0021-desktop-packaging-pyinstaller.md).
