# Explain-the-Code Practice Guide

Use this guide to practice a two-to-five-minute explanation. The strongest
answer keeps returning to the operator problem, the preservation boundary, and
the evidence in the code.

## Opening answer

“Email Vault is a Python/FastAPI proof of concept for moving important Gmail
threads into verified, portable local exports before inbox cleanup. The system
accepts a canonical thread snapshot, authenticates and validates it, classifies
and routes it, sanitizes email HTML, writes artifacts such as EML, text,
metadata, and a manifest, verifies checksums, and records an auditable state in
SQLite. The important product decision is that Gmail mutation is a separate
post-completion handoff, and the current POC keeps that mutation disabled.”

## Practice questions and strong answers

### What problem does it solve?

Inbox cleanup creates a preservation and trust problem. People need a portable
copy, but exporting and deleting in one step makes failure hard to recover
from. Email Vault makes the safe order explicit: preserve, verify, record, then
consider cleanup. The product scope is described in `docs/product-scope.md` and
the workflow is coordinated in `services/api/app/services/archive.py`.

### Walk me through one request.

The request enters `POST /archive/thread` in `api/routes.py`. Dependencies
provide identity, repository, renderer, storage, and attachment adapters. The
route converts the Pydantic request to domain objects and calls
`ArchiveCoordinator.preserve`. That method validates, plans the revision,
sanitizes content, builds artifacts, stages and verifies them, persists audit
states, and returns a result with Gmail finalization disabled.

### Why is the Gmail action separate?

Because preservation and deletion have different risk profiles. If rendering or
storage fails, Gmail should not be changed. The state machine in `domain/state.py`
only allows finalization after `COMPLETED`, and the separate routes make that
boundary observable and testable.

### How do you handle duplicate exports?

`domain/contracts.py:snapshot_fingerprint` produces a deterministic SHA-256
fingerprint of the canonical thread. `RevisionPlanner` scopes its lookup by
owner and compares the fingerprint, so retries can return `DUPLICATE` instead
of silently creating another record.

### What happens to unsafe email HTML?

`services/sanitization/html.py` removes unsafe tags, attributes, and URL
schemes and provides plain text. `rendering/snapshot.py` turns that result into
the renderer input. The Playwright boundary also blocks network access and
disables JavaScript. The tests include malicious HTML and tracking-pixel cases.

### How do you know an export is complete?

The writer creates server-controlled artifacts, computes checksums, and the
storage provider verifies the staged files. Only a verified storage result can
append `VERIFIED`, and only that state can transition to `COMPLETED`.

### Why SQLite and local storage?

The project is intentionally local-first at this stage. SQLite makes revision
and audit behavior inspectable without claiming a hosted production database;
the storage protocol leaves room for a future provider. The decision is also
captured in ADR 0005.

### What is the current limitation?

There is no live Gmail listing/import, whole-mailbox sync, hosted production
deployment, cloud storage provider, or enabled Gmail mutation. OAuth readiness
and encrypted local token storage are present, but real Gmail import is the
next private implementation step. The README’s “What this POC intentionally
does not do yet” section is the source of truth.

### What would make it production-ready?

Complete read-only Gmail import, validate OAuth scopes and HTTPS deployment,
define a durable storage/backup policy, add operational monitoring and retry
semantics, run a privacy/security review, and implement reversible Gmail
actions behind explicit user review. I would also add end-to-end tests against
an isolated Google test account before enabling mutation.

### How would you improve the architecture next?

I would keep the coordinator and domain contracts stable while adding a Gmail
adapter behind a protocol. That keeps provider-specific pagination, rate limits,
and retries out of the preservation core. Then I would add an idempotent import
job model and a durable job queue only when live mailbox scale requires it.

### What evidence shows this is more than a mockup?

The repository has executable CLI workflows, a local web demo, SQLite audit
state, artifact checksum verification, signed add-on boundaries, renderer
adapters, synthetic fixtures, and focused tests across those seams. The claim is
still a POC claim, not a production backup guarantee.

## Whiteboard sequence

Draw this in order:

```text
Gmail/Add-on or fixture
  -> signed/authenticated request
  -> canonical contract + revision plan
  -> classify and route
  -> sanitize
  -> write artifacts
  -> verify storage
  -> SQLite audit: COMPLETED
  -> optional, separate Gmail finalization
```

For every arrow, name one file. That turns a product explanation into a code
explanation instead of a list of technologies.

## Interview habits

- State the current boundary before describing the future roadmap.
- Use “the code proves” only when you can point to a test or implementation.
- Mention the tradeoff behind local-first and synthetic data.
- Explain one failure path, not only the happy path.
- Distinguish planned Gmail action, recorded intent, and actual Gmail mutation.
