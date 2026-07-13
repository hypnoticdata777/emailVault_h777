# Current State Audit

## Repository Tree

At the start of this work the repository contained only `.git/` metadata. Git
reported: `No commits yet on main...origin/main [gone]`.

## Current Architecture and Stack

No application architecture, dependency manifest, tests, CI, migrations, Docker
files, README, or source entry points existed before this P0/P1 foundation.

The P1 foundation uses Python standard-library modules so the core contracts and
invariant tests can run immediately without package installation. P2 adds
FastAPI/Pydantic modules behind optional dependencies.

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
- No Google identity verification exists yet.
- No service orchestration layer wires identity, duplicate lookup, and revision
  persistence into the archive route yet.
- No sanitizer, renderer, attachment fetcher, storage provider, PDF generation,
  audit event store, or Gmail finalization callback exists yet.
- No CI workflow exists yet; the project has no remote commit history to extend.
- No Docker runtime exists yet.

## Risky or Conflicting Code

No pre-existing code was present. The main risk is that early contracts may need
to be translated to Pydantic models when FastAPI is introduced.

## Recommended Minimal Changes

1. Keep this P0/P1 foundation focused and avoid implementing Gmail mutation.
2. Add FastAPI and Pydantic v2 in P2 when the first API route is created.
3. Add a SQLite-backed repository interface before any renderer or storage work.
4. Add CI once package dependencies and command choices are stable.
