# ADR 0005: Local-First Before Hosted SaaS

## Status

Accepted.

## Context

Email Vault is intended to become both a useful personal inbox tool and a
marketable subscription product. The product needs Gmail access, export storage,
classification, review, and optional Gmail cleanup actions.

Hosted SaaS adds additional complexity early: production OAuth verification,
restricted Gmail scopes, multi-tenant security, billing, privacy disclosures,
data deletion workflows, and possible external security assessment. Those are
real requirements for a commercial version, but they should not block the first
usable tool for the project owner.

## Decision

Build v0.2 as a local-first Gmail offloader and inbox cleaner while preserving
SaaS-ready boundaries.

The first working target is:

- one user's Gmail account;
- user-selected local filesystem storage root;
- PC folder, USB drive, external drive, or OneDrive-synced folder;
- verified export package before cleanup;
- label plus archive as the first cleanup action after verification;
- trash/delete deferred to Free Space Mode;
- explainable routing and dry-run review before cleanup;
- portable data port for downstream AI/search tools.

The core commercial implementation should live in a private repository if the
product will be marketed as a subscription tool. Public portfolio material can
show sanitized architecture, screenshots, and synthetic walkthroughs without
exposing the full implementation.

## Consequences

- The local tool can be useful sooner for a real overloaded inbox.
- Direct folder export supports PC, USB, and OneDrive sync without needing cloud
  provider integrations.
- The project can iterate safely before broad OAuth verification.
- The code must maintain clean boundaries so local components can later become
  SaaS workers, APIs, and dashboards.
- Public repo/demo wording must avoid implying production Gmail cleanup or
  storage reduction until those paths are validated.
