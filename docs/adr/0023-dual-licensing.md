# ADR-0023: Dual licensing — AGPL-3.0 + commercial

- Status: Accepted
- Date: 2026-06-15
- Deciders: Felipe Carvajal Brown

## Context

Keel should be free and open for individuals and open projects, while still
allowing a paid, closed product and protecting against someone running a modified
version as a closed network service.

## Decision

**Dual-license** the project:

- **Open source: GNU AGPL-3.0** (`LICENSE`, per-file headers). Free to use,
  study, modify, share — but distributing it or running a modified version as a
  network service requires releasing source under the AGPL too.
- **Commercial license** (`COMMERCIAL-LICENSE.md`). To build on Keel inside a
  closed-source product/service without the AGPL's copyleft, take a commercial
  license from the author.

This is the legal basis for the commercial license; the LGPL GUI stack
(ADR-0019) keeps any closed build lawful. The GUI's own licensing/funding model
evolved in [ADR-0025](0025-gui-noncommercial-license-and-donations.md) (free
non-commercial + donations; USD 20/seat commercial) — this engine dual-license
still holds.

## Consequences

- Individuals/open projects use it freely; companies wanting it closed pay.
- AGPL's network clause protects against closed SaaS forks.
- Formal legal review remains optional/future.

## References

- `LICENSE`; `COMMERCIAL-LICENSE.md`; README "License".
- Related: [ADR-0019](0019-gui-toolkit-pyside6.md), [ADR-0024](0024-distribution-and-pricing.md).
