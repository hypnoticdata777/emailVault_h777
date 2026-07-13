# Current State Audit

## Repository Tree

At the start of this work the repository contained only `.git/` metadata. Git
reported: `No commits yet on main...origin/main [gone]`.

## Current Architecture and Stack

No application architecture, dependency manifest, tests, CI, migrations, Docker
files, README, or source entry points existed before this P0/P1 foundation.

The P1 foundation uses Python standard-library modules so the core contracts and
invariant tests can run immediately without package installation. P2 adds
FastAPI/Pydantic modules behind optional dependencies. Early P3 work adds
dependency-light sanitization, renderer-safe snapshot preparation, artifact
manifest planning, and the PDF renderer boundary ADR.

## What Already Works

- Canonical archive request, response, state, and error concepts are represented.
- Synthetic JSON fixtures can be loaded and validated.
- Attachment allowlist and size limits are enforced by contract validation.
- Storage path helper rejects traversal, absolute paths, nested paths, and null
  bytes.
- Redaction helper prevents sensitive fixture values from being emitted into
  structured log extras.
- State transition policy blocks Gmail finalization before storage verification.
- Duplicate fingerprinting is deterministic and changes when a thread gains a
  message.
- FastAPI application factory, `/health`, and `/archive/thread` stub route exist
  when optional API dependencies are installed.
- The archive route requires a bearer identity and returns Gmail finalization
  disabled until archive execution is implemented.
- SQLite-backed revision persistence stores owner-scoped archive references and
  ordered audit events without storing email content.
- The archive coordinator now uses a safe revision planner for duplicate,
  new-thread, and updated-thread decisions without writing completed records.
- The local storage provider can stage generated artifacts and verify checksums
  without marking revisions completed.
- HTML sanitization removes hostile tags and attributes, blocks remote image
  sources, and provides plain-text fallback output.
- Sanitized message normalization produces safe HTML plus guaranteed plain text
  for future rendering.
- Renderer-safe snapshots keep raw email HTML out of renderer inputs.
- Artifact manifest planning declares future PDF, metadata JSON, and manifest
  JSON outputs with server-generated trusted filenames.
- ADR 0003 records the PDF renderer boundary before renderer implementation.
- Local API runs can bootstrap the configured SQLite schema with
  `python -m services.api.app.cli init-db`.
- Developer setup, current API behavior, and data model notes are documented in
  `docs/development.md`, `docs/api.md`, and `docs/data-model.md`.
- Security and privacy boundaries are documented in
  `docs/security-and-privacy.md`.

## Setup and Run Commands

```powershell
python -m unittest discover -s tests
python -m pip install -e ".[api,test]"
uvicorn services.api.app.main:app --reload
```

No dependency installation is required for the standard-library contract tests.
The API skeleton requires optional dependencies.

## Gaps Against Target POC

- No Gmail Workspace Add-on exists yet.
- No HTTPS API entry point exists yet.
- No production Google identity verification exists yet; the local verifier is
  synthetic.
- No PDF renderer implementation exists yet.
- No attachment fetcher or permitted attachment copy flow exists yet.
- No production audit event service or completion state transition exists yet.
- No Gmail finalization callback exists yet.
- No CI workflow exists yet.
- No Docker runtime exists yet.

## Risky or Conflicting Code

No pre-existing code was present. The main risk is still premature completion:
rendering, storage staging, and Gmail finalization must remain separate until
storage verification and persisted state transitions are implemented. The
current API tests intentionally keep Gmail finalization disabled.

## Recommended Minimal Changes

1. Add renderer tests and a minimal PDF rendering scaffold from ADR 0003.
2. Keep renderer/storage integration behind blocked-network, cleanup, and
   checksum-verification tests.
3. Add CI once package dependencies and command choices are stable.
