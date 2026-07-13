# Email Vault POC

Email Vault is a portfolio-quality proof of concept for preserving the accessible
snapshot of one opened Gmail thread. The current build contains the P0/P1
foundation plus the first P2 API and persistence boundaries.

No Gmail mutation, production OAuth, cloud storage, AI, deletion, or deployment
behavior is implemented in this phase.

## Current Status

Done:

- Product scope, requirements, architecture notes, and ADRs.
- Canonical archive contracts, state model, and controlled error categories.
- Synthetic email fixtures and invariant tests.
- FastAPI app skeleton with `/health` and `/archive/thread`.
- Pydantic v2 request/response schemas.
- Google identity verification boundary with a synthetic local verifier.
- SQLite revision/audit repository for local P2 persistence tests.
- Safe revision planner for duplicate, new-thread, and updated-thread decisions.
- Local storage provider boundary that stages generated artifacts and verifies
  checksums without marking revisions completed.
- Security and privacy boundaries documented for public-ready development.
- First P3 sanitizer pass for hostile HTML, remote image blocking, and
  plain-text fallback.
- Archive coordinator that validates, fingerprints, checks duplicates, and keeps
  Gmail finalization disabled until storage verification exists.

Next:

1. Expand sanitizer coverage and normalize sanitized message bodies.
2. Add sanitizer tests for more edge cases and attachment-adjacent HTML.
3. Add renderer/storage integration only after sanitization tests are stable.

## Thread vs Email

In Gmail, a **thread** is the conversation container. It can include one message
or many messages with the same conversation history.

An **email message** is one individual sent or received item inside that thread.
Email Vault targets one opened Gmail thread because preserving the whole
conversation is safer than preserving only the currently visible message. If a
thread gets a new message later, that should become a new immutable revision of
the same vault thread.

## Quick Start

```powershell
python -m unittest discover -s tests
```

The foundational contract tests use only the Python standard library. To run the
P2 FastAPI skeleton tests and local API, install the optional API/test
dependencies:

```powershell
python -m pip install -e ".[api,test]"
python -m services.api.app.cli init-db
python -m pytest
python -m uvicorn services.api.app.main:app --reload
```

The archive route is intentionally not a real preservation endpoint yet. In P2,
it validates input and checks duplicate state, but it does not render PDFs, stage
storage, write completed revisions, label Gmail, mark Gmail read, or archive
Gmail messages.

Key docs:

- `docs/development.md`
- `docs/api.md`
- `docs/data-model.md`
- `docs/security-and-privacy.md`
