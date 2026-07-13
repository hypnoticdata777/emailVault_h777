# Email Vault POC

Email Vault is a portfolio-quality proof of concept for preserving the accessible
snapshot of one opened Gmail thread. The current build contains the P0/P1
foundation plus the first P2/P3 API, persistence, rendering, and identity
boundaries.

No Gmail mutation, cloud storage, AI, deletion, or deployment behavior is
implemented in this phase.

## Current Status

Done:

- Product scope, requirements, architecture notes, and ADRs.
- Canonical archive contracts, state model, and controlled error categories.
- Synthetic email fixtures and invariant tests.
- FastAPI app skeleton with `/health` and `/archive/thread`.
- Pydantic v2 request/response schemas.
- Google identity verification boundary with synthetic local mode and
  configurable Google ID-token verification mode.
- SQLite revision/audit repository for local P2 persistence tests.
- Safe revision planner for duplicate, new-thread, and updated-thread decisions.
- Local storage provider boundary that stages generated artifacts and verifies
  checksums without marking revisions completed.
- Security and privacy boundaries documented for public-ready development.
- First P3 sanitizer pass for hostile HTML, remote image blocking, and
  plain-text fallback.
- Normalized sanitized message-body output for safe HTML and guaranteed plain
  text.
- Renderer-safe snapshot preparation that keeps raw email HTML out of future PDF
  inputs.
- Expanded sanitizer coverage for table-heavy emails and attachment-adjacent
  unsafe links.
- Artifact manifest planning for future PDF, metadata JSON, and manifest JSON
  outputs with server-generated filenames only.
- PDF renderer boundary ADR covering Playwright/Chromium, blocked network
  requests, disabled JavaScript, and temp workspace cleanup requirements.
- Adapter-based PDF renderer scaffold with tests for sanitized input, blocked
  network policy, disabled JavaScript, PDF bytes, and temp workspace cleanup.
- Playwright/Chromium PDF adapter boundary with tests for JavaScript-disabled
  context creation, route abort handling, PDF options, and close calls.
- Opt-in browser-backed renderer smoke test path for local Chromium PDF checks.
- Renderer PDF output can be staged through the storage provider and checksum
  verified without marking revisions completed.
- Archive coordinator can persist a verified storage revision and audit
  `RENDERED`, `STAGED`, and `VERIFIED` without completing or finalizing Gmail.
- Archive coordinator can append `COMPLETED` only after the verified storage
  audit boundary, still without enabling Gmail finalization.
- Gmail finalization instructions can be requested only after `COMPLETED`, and
  callback results can be recorded only after finalization is pending.
- Archive coordinator that validates, fingerprints, checks duplicates, and keeps
  Gmail finalization disabled on the archive route until the end-to-end add-on
  flow exists.
- Archive route can run the backend preservation path for generated PDFs:
  sanitize, render, stage storage, verify checksums, persist the revision, append
  `COMPLETED`, and still leave Gmail finalization disabled.
- GitHub Actions CI runs the stable Python 3.12 test suite with API/test
  dependencies on push and pull request.
- Production identity blocker reduced to configuration and real Google OAuth
  project validation, with unit tests covering the verifier boundary.
- Gmail Workspace Add-on shell with homepage/contextual cards, current-message
  preview behavior, preference capture, and tests proving it does not mutate
  Gmail.
- Docker runtime packaging for the API with non-root execution, `/health`
  healthcheck, persistent `/data` paths, and CI build validation.

Next:

1. Wire the add-on to the backend archive route once request signing and
   deployment configuration are ready.
2. Add permitted attachment copy and metadata/manifest artifact output.
3. Validate a real Google OAuth client ID in a private environment before any
   real-data demo.

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

To prepare local PDF rendering, install the renderer optional dependency and
Chromium browser runtime:

```powershell
python -m pip install -e ".[renderer]"
python -m playwright install chromium
```

Run the opt-in browser-backed renderer smoke test after installing Chromium:

```powershell
$env:EMAIL_VAULT_RUN_RENDERER_SMOKE = "1"
python -m unittest tests.test_playwright_renderer_smoke
Remove-Item Env:\EMAIL_VAULT_RUN_RENDERER_SMOKE
```

The archive route can preserve the generated PDF path when API and renderer
dependencies are installed. It still does not label Gmail, mark Gmail read, or
archive Gmail messages.

Key docs:

- `docs/development.md`
- `docs/api.md`
- `docs/addon.md`
- `docs/deployment.md`
- `docs/data-model.md`
- `docs/security-and-privacy.md`
