# Current State Audit

## Repository Tree

At the start of this work the repository contained only `.git/` metadata. Git
reported: `No commits yet on main...origin/main [gone]`.

## Current Architecture and Stack

No application architecture, dependency manifest, tests, CI, migrations, Docker
files, README, or source entry points existed before this P0/P1 foundation.

The initial foundation now uses Python standard-library modules so the contracts
and invariant tests can run immediately without package installation. This is a
deliberate P1 compromise because the local environment did not have Pydantic or
pytest installed. Later API phases should introduce FastAPI and Pydantic v2.

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

## Setup and Run Commands

```powershell
python -m unittest discover -s tests
```

No dependency installation is required for the current foundation.

## Gaps Against Target POC

- No Gmail Workspace Add-on exists yet.
- No HTTPS API entry point exists yet.
- No Google identity verification exists yet.
- No persistence layer, migrations, or repository implementation exists yet.
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

